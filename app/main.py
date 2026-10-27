"""Local-only learning game. Learner code runs as the current OS user, not in a sandbox."""
import json
import math
import os
import random
import secrets
import shutil
import signal
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
from datetime import date, timedelta
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.middleware.trustedhost import TrustedHostMiddleware

ROOT=Path(__file__).resolve().parents[1]
DATA=Path(os.environ.get('GAUNTLET_DATA',ROOT/'data'))
PORT=os.environ.get('GAUNTLET_PORT','8000')
WORK=Path(os.environ.get('GAUNTLET_WORKSPACE',ROOT/'workspace')).resolve()
DATA.mkdir(parents=True,exist_ok=True); WORK.mkdir(parents=True,exist_ok=True)
CUR=json.loads((ROOT/'content/curriculum.json').read_text(encoding='utf-8'))
BOSSES=json.loads((ROOT/'content/bosses.json').read_text(encoding='utf-8'))
LESSONS=json.loads((ROOT/'content/lessons.json').read_text(encoding='utf-8'))
PATHS=json.loads((ROOT/'content/paths.json').read_text(encoding='utf-8'))
TIERS=PATHS['tiers']
# Field overlays: wording (and, where the original ties the code to electronics, a whole
# alternative contract) for players from a given field. See content/fields/*.json.
FIELDS={f.stem:json.loads(f.read_text(encoding='utf-8')) for f in sorted((ROOT/'content/fields').glob('*.json'))}
ITEMS={x['id']:x for x in CUR['levels']+BOSSES}
LOCK=threading.RLock()
BUSY=False
app=FastAPI(title='Gauntlet Academy',docs_url=None,redoc_url=None)
app.add_middleware(TrustedHostMiddleware,allowed_hosts=['localhost','127.0.0.1','testserver'])

@app.middleware('http')
async def local_only(request:Request,call_next):
    if request.method not in ('GET','HEAD'):
        if request.headers.get('X-Gauntlet')!='local': return JSONResponse({'detail':'Local UI header required'},403)
        origin=request.headers.get('origin')
        if origin and origin not in (f'http://localhost:{PORT}',f'http://127.0.0.1:{PORT}','http://testserver'):
            return JSONResponse({'detail':'Foreign origin rejected'},403)
    response=await call_next(request)
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Referrer-Policy']='no-referrer'
    response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'"
    return response

def initial():
    return dict(xp=0,hp=100,completed=[],quiz_passed=[],lessons_read=[],keys=[],badges=[],bosses=[],quiz_streak=0,best_streak=0,streak=0,last_active=None,quiz_scores={},combos={},review={},daily_reward=None,session=None,profile=None,challenges=[],boss_hp={str(w):100 for w in range(1,5)})

def read():
    with sqlite3.connect(DATA/'save.sqlite3') as db:
        db.execute('CREATE TABLE IF NOT EXISTS save (id INTEGER PRIMARY KEY, body TEXT NOT NULL)')
        row=db.execute('SELECT body FROM save WHERE id=1').fetchone()
    # Older saves predate some fields; fill them with defaults.
    return {**initial(),**json.loads(row[0])} if row else initial()

def lesson_done(id,s):
    # A passed quiz from an older save counts as a finished lesson.
    return id in s['lessons_read'] or id in s['quiz_passed']

def save(s):
    with sqlite3.connect(DATA/'save.sqlite3') as db:
        db.execute('CREATE TABLE IF NOT EXISTS save (id INTEGER PRIMARY KEY, body TEXT NOT NULL)')
        db.execute('INSERT OR REPLACE INTO save VALUES (1,?)',(json.dumps(s),))

def skipped(s):
    return set(s['profile']['skipped']) if s['profile'] else set()

def path_worlds(s):
    return s['profile']['worlds'] if s['profile'] else [1,2,3,4]

def cleared(id,s):
    # Placed-out levels count as done for unlocking, but earn nothing.
    return id in s['completed'] or id in skipped(s)

def boss_done(w,s):
    # Boot Camp (world 0) has no project; finishing its four missions completes it.
    if w==0: return all(cleared(f'0.{n}',s) for n in range(1,5))
    return str(w) in s['bosses'] or f'{w}.boss' in skipped(s)

def penalty(s):
    # Beginners lose less health per mistake.
    return 5 if s['profile'] and s['profile']['tier']=='beginner' else 10

def build_open(id,s):
    # Build normally follows a passed quiz; challenge mode goes straight to it.
    return 'quiz' not in ITEMS[id] or id in s['quiz_passed'] or id in s['challenges']

def world_open(w,s):
    # Rooms outside the learner's goal never block the rooms after them.
    return all(boss_done(p,s) for p in path_worlds(s) if p<w)

def active(s):
    today=date.today().isoformat()
    if s['last_active']!=today:
        s['streak']=s['streak']+1 if s['last_active']==(date.today()-timedelta(days=1)).isoformat() else 1
        s['last_active']=today

def unlocked(id,s):
    item=ITEMS[id];w=item['world']
    if not world_open(w,s): return False
    if id.endswith('boss'): return str(w) in s['keys'] or id in skipped(s)
    n=int(id.split('.')[1])
    return n==1 or cleared(f'{w}.{n-1}',s)

def public_q(q):
    return {k:v for k,v in q.items() if k not in ('answer','explanation')}

def session_view(s):
    t=s['session']
    if not t: return None
    out={k:v for k,v in t.items() if k!='questions'}
    out['total']=len(t['questions'])
    out['question']=public_q(t['questions'][t['index']]) if t['index']<len(t['questions']) else None
    return out

def view(s):
    result={k:v for k,v in s.items() if k not in ('session','review')}
    result['level']=1+s['xp']//200
    result['level_xp']=s['xp']%200
    worlds=path_worlds(s)
    result['path_worlds']=worlds
    result['current_world']=next((w for w in worlds if not boss_done(w,s)),worlds[-1])
    result['open_worlds']=[w for w in range(5) if world_open(w,s)]
    result['session']=session_view(s)
    result['penalty']=penalty(s)
    result['field_examples']=bool(s['profile']) and s['profile']['field'] in FIELDS
    result['workspace']=str(WORK)
    return result

def alive(s):
    if s['hp']<=0: raise HTTPException(409,'HP depleted. Recover at the med bay, then retry.')

def item_or_404(id):
    if id not in ITEMS: raise HTTPException(404,'Unknown quest')
    return ITEMS[id]

def patched(base,patch):
    # `patch` maps list positions (as strings) to replacements; everything else is kept.
    out=list(base)
    for i,v in (patch or {}).items(): out[int(i)]=v
    return out

def field_overlay(s):
    return FIELDS.get(s['profile']['field'],{}) if s['profile'] else {}

def field_level(id,s):
    return field_overlay(s).get('levels',{}).get(id)

def localized(item,s):
    """The mission as this player sees it: field wording, and for variant missions the field's own contract."""
    ov=field_level(item['id'],s)
    if not ov: return item
    out={**item,**{k:ov[k] for k in ('title','quest','hints') if k in ov}}
    if ov.get('variant'): out['path']=item['path'].replace('.py',f"_{s['profile']['field']}.py")
    if 'quiz' in item: out['quiz']=patched(item['quiz'],ov.get('quiz'))
    return out

def lesson_view(id,s):
    base=LESSONS.get(id,{});ov=field_level(id,s) or {}
    return dict(summary=ov.get('summary',base.get('summary','')),pages=patched(base.get('pages',[]),ov.get('pages')))

def test_key(id,s):
    ov=field_level(id,s)
    return f"{id}_{s['profile']['field']}" if ov and ov.get('variant') else id

def gate_questions(w,s):
    return patched(CUR['gatekeepers'][w],field_overlay(s).get('gatekeepers',{}).get(w))

@app.get('/api/state')
def state():
    with LOCK: return view(read())

@app.get('/api/curriculum')
def curriculum():
    with LOCK:
        s=read(); items=[]
        for item in ITEMS.values():
            item=localized(item,s)
            out={k:v for k,v in item.items() if k!='quiz'}
            out['unlocked']=unlocked(item['id'],s)
            lesson=lesson_view(item['id'],s)
            out['lesson_pages']=lesson['pages']
            out['summary']=lesson['summary']
            out['lesson_done']=lesson_done(item['id'],s)
            items.append(out)
        return dict(worlds=CUR['worlds'],items=items)

class Start(BaseModel):
    kind:str
    target:str=''
    timed:bool=False

@app.post('/api/quiz/start')
def start(body:Start):
    with LOCK:
        s=read();alive(s)
        if body.kind=='level':
            item=localized(item_or_404(body.target),s)
            if 'quiz' not in item or not unlocked(body.target,s): raise HTTPException(403,'Finish the previous quest first')
            if not lesson_done(body.target,s): raise HTTPException(403,'Finish the lesson before taking its quiz')
            questions=[dict(q,review_id=body.target+':'+str(i)) for i,q in enumerate(item['quiz'])]
        elif body.kind=='gate':
            if body.target not in ('1','2','3','4'): raise HTTPException(404,'Unknown world')
            if not all(cleared(f'{body.target}.{i}',s) for i in range(1,5)): raise HTTPException(403,'Complete all four coding quests first')
            questions=[dict(q) for q in gate_questions(body.target,s)]
        elif body.kind=='daily':
            pool=[dict(q,review_id=item['id']+':'+str(i)) for item in map(lambda x:localized(x,s),CUR['levels']) if item['id'] in s['completed'] for i,q in enumerate(item['quiz'])]
            if not pool: raise HTTPException(403,'Complete your first coding quest to open Training Grounds')
            # Weighted random review favors weak/overdue cards; with one completed level, repeats fill five slots.
            now=time.time()
            def weight(q):
                r=s['review'].get(q['review_id'],{})
                return 1+3*(r.get('due',0)<=now)+r.get('misses',0)
            questions=[]; remaining=pool.copy()
            for _ in range(5):
                if not remaining: remaining=pool.copy()
                picked=random.choices(remaining,weights=[weight(q) for q in remaining],k=1)[0]
                questions.append(picked.copy());remaining.remove(picked)
        else: raise HTTPException(400,'Unknown trial type')
        # Shuffle choices without leaking the answer to the browser.
        for q in questions:
            pairs=list(enumerate(q['options']));random.shuffle(pairs)
            answer=q['answer'];q['options']=[p[1] for p in pairs];q['answer']=next(i for i,p in enumerate(pairs) if p[0]==answer)
        t=dict(id=secrets.token_hex(12),kind=body.kind,target=body.target,questions=questions,index=0,correct=0,finished=False,passed=False,deadline=time.time()+300 if body.timed else None)
        s['session']=t;active(s);save(s)
        return session_view(s)

class Answer(BaseModel):
    session_id:str
    index:int
    choice:int=Field(ge=0,le=3)

@app.post('/api/quiz/answer')
def answer(body:Answer):
    with LOCK:
        s=read();alive(s);t=s['session']
        if not t or t['id']!=body.session_id or t['finished'] or body.index!=t['index']: raise HTTPException(409,'This question is no longer active')
        if t['deadline'] and time.time()>t['deadline']:
            t['finished']=True;save(s)
            raise HTTPException(409,'Time expired. Start a fresh trial.')
        q=t['questions'][t['index']];correct=body.choice==q['answer']
        if correct: t['correct']+=1;s['quiz_streak']+=1
        else: s['hp']=max(0,s['hp']-penalty(s));s['quiz_streak']=0
        s['best_streak']=max(s['best_streak'],s['quiz_streak'])
        rid=q.get('review_id')
        if rid:
            r=s['review'].setdefault(rid,dict(interval=0,misses=0))
            r['interval']=min(30,max(1,r['interval']*2)) if correct else 0
            r['misses']+=int(not correct);r['due']=time.time()+r['interval']*86400
        t['index']+=1
        if t['index']==len(t['questions']) or s['hp']==0:
            t['finished']=True
            needed=3 if t['kind']=='level' else 8 if t['kind']=='gate' else 0
            t['passed']=t['correct']>=needed and s['hp']>0
            scorekey=t['kind']+':'+t['target']
            s['quiz_scores'][scorekey]=max(s['quiz_scores'].get(scorekey,0),t['correct'])
            if t['passed'] and t['kind']=='level':
                if t['target'] not in s['quiz_passed']:
                    s['quiz_passed'].append(t['target']);s['xp']+=30
                s['combos'][t['target']]=1.5
            elif t['passed'] and t['kind']=='gate':
                if t['target'] not in s['keys']:
                    s['keys'].append(t['target']);s['xp']+=100
                    s['badges'].append('Boss Key '+t['target'])
            elif t['kind']=='daily' and t['index']==5 and s['daily_reward']!=date.today().isoformat():
                s['xp']+=t['correct']*10;s['daily_reward']=date.today().isoformat()
        active(s);save(s)
        return dict(correct=correct,explanation=q['explanation'],correct_answer=q['options'][q['answer']],state=view(s))

class Lesson(BaseModel):
    id:str

@app.post('/api/lesson/complete')
def complete_lesson(body:Lesson):
    with LOCK:
        s=read();item=item_or_404(body.id)
        if 'quiz' not in item or not unlocked(body.id,s): raise HTTPException(403,'This lesson is locked')
        if body.id not in s['lessons_read']: s['lessons_read'].append(body.id)
        active(s);save(s)
        return view(s)

@app.post('/api/challenge')
def challenge(body:Lesson):
    # Skip the lesson and quiz. The build then earns base XP, without the quiz bonus.
    with LOCK:
        s=read();item=item_or_404(body.id)
        if 'quiz' not in item or not unlocked(body.id,s): raise HTTPException(403,'This mission is locked')
        if body.id not in s['challenges']: s['challenges'].append(body.id)
        active(s);save(s)
        return view(s)

@app.post('/api/recover')
def recover():
    with LOCK:
        s=read();s['hp']=100;s['quiz_streak']=0;s['session']=None;save(s)
        return view(s)

class Quest(BaseModel):
    id:str

@app.post('/api/initialize')
def initialize(body:Quest):
    item=item_or_404(body.id)
    with LOCK:
        s=read();item=localized(item,s)
        if not unlocked(body.id,s) or not build_open(body.id,s): raise HTTPException(403,'Pass the knowledge trial or earn the Boss Key first')
        relative=Path(item['path']); dest=WORK/relative
        if not dest.resolve().is_relative_to(WORK): raise HTTPException(400,'Workspace path escapes project')
        dest.parent.mkdir(parents=True,exist_ok=True)
        source=ROOT/'templates'/relative
        sources=[p for p in source.parent.iterdir() if p.is_file()] if body.id.endswith('boss') else [source]
        created=[]
        for src in sources:
            target=dest.parent/src.name
            if target.is_symlink(): raise HTTPException(400,'Quest files cannot be symlinks')
            if not target.exists(): shutil.copy2(src,target);created.append(str(target))
        if body.id.endswith('boss') and item['world']>=2:
            helper=dest.parent/'gauntlet_ai.py'
            if not helper.exists(): shutil.copy2(ROOT/'gauntlet_ai.py',helper)
        return dict(path=str(dest),created=created,message='Files initialized. Existing work is preserved.' if created else 'Quest files already exist; your work was preserved.')

def kill_tree(proc):
    """Kill the verification process and any children it started (process group on Unix, taskkill on Windows)."""
    if os.name=='nt':
        subprocess.run(['taskkill','/F','/T','/PID',str(proc.pid)],capture_output=True)
        return
    try: os.killpg(proc.pid,signal.SIGKILL)
    except ProcessLookupError: pass

def run_verification(id):
    test=ROOT/'verification'/('test_'+id.replace('.','_')+'.py')
    env={k:v for k,v in os.environ.items() if k in ('PATH','HOME','TMPDIR','LANG','SYSTEMROOT','USERPROFILE','TEMP','TMP','PATHEXT','COMSPEC','APPDATA','LOCALAPPDATA')}
    env.update(PYTHONUTF8='1',GAUNTLET_WORKSPACE=str(WORK),PYTHONPATH=str(ROOT),PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',TOKENIZERS_PARALLELISM='false',ANONYMIZED_TELEMETRY='false')
    # A separate process permits timeout/termination; this is NOT an OS security sandbox.
    cmd=[sys.executable,str(ROOT/'app/runner.py'),str(test)]
    with tempfile.TemporaryFile() as log:
        proc=subprocess.Popen(cmd,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        timed_out=False
        try: proc.wait(timeout=45)
        except subprocess.TimeoutExpired:
            timed_out=True;kill_tree(proc);proc.wait()
        finally:
            # Remove lingering child processes created by learner code.
            kill_tree(proc)
        log.seek(0);output=log.read(24000).decode('utf-8',errors='replace')
    if timed_out: output+='\nVerification exceeded 45 seconds. Check for infinite loops or network calls.'
    return proc.returncode==0 and not timed_out,output

@app.post('/api/verify')
def verify(body:Quest):
    global BUSY
    item=item_or_404(body.id)
    with LOCK:
        s=read();alive(s);item=localized(item,s);key=test_key(body.id,s)
        if not unlocked(body.id,s) or not build_open(body.id,s): raise HTTPException(403,'Quest is locked')
        target=WORK/item['path']
        if not target.exists(): raise HTTPException(409,'Initialize Quest Files first')
        if not target.resolve().is_relative_to(WORK): raise HTTPException(400,'Quest path escapes workspace')
        if BUSY: raise HTTPException(409,'A verification run is already active')
        BUSY=True
    try: passed,output=run_verification(key)
    finally:
        with LOCK: BUSY=False
    with LOCK:
        s=read();reward=0
        if passed and body.id not in s['completed']:
            s['completed'].append(body.id)
            reward=300 if body.id.endswith('boss') else int(100*s['combos'].get(body.id,1))
            s['xp']+=reward;s['hp']=min(100,s['hp']+20)
            if body.id.endswith('boss'):
                w=str(item['world']);s['bosses'].append(w);s['boss_hp'][w]=0
                s['badges'].append(['Scribe Slayer','Nexus Guardian','Hydra Tamer','The Architect'][item['world']-1])
            elif body.id=='1.1': s['badges'].append('First Signal')
            elif body.id.startswith('0.') and boss_done(0,s): s['badges'].append('Boot Camp Graduate')
        elif not passed: s['hp']=max(0,s['hp']-penalty(s))
        active(s);save(s)
        return dict(passed=passed,output=output,reward=reward,state=view(s))

# ---------------------------------------------------------------- onboarding and paths

def placement_tier(experience,choices):
    if experience=='never': return 'beginner'
    right={t:0 for t in TIERS}
    for q,c in zip(PATHS['placement'],choices): right[q['tier']]+=c==q['answer']
    if right['beginner']<2 or right['intermediate']<1: return 'beginner'
    if right['intermediate']<2 or right['advanced']<1: return 'intermediate'
    return 'advanced'

def build_plan(answers,choices):
    tier=placement_tier(answers['experience'],choices)
    # New and early coders who place as beginners start in Boot Camp.
    bootcamp=answers['experience'] in ('never','little') and tier=='beginner'
    worlds=[0]*bootcamp+PATHS['goals'][answers['goal']]
    rank=TIERS.index(tier)
    skip=[id for id,t in PATHS['levels'].items() if int(id.split('.')[0]) in worlds and TIERS.index(t)<rank]
    # A fully placed-out room skips its project too, except the last room: every path ends with a project.
    skip+=[f'{w}.boss' for w in worlds[:-1] if w and all(f'{w}.{n}' in skip for n in range(1,5))]
    hours=PATHS['hours_per_item']
    missions=sum(1 for id in PATHS['levels'] if int(id.split('.')[0]) in worlds and id not in skip)
    projects=sum(1 for w in worlds if w and f'{w}.boss' not in skip)
    total=missions*hours['mission']+projects*(hours['checkpoint']+hours['project'])
    return dict(answers,tier=tier,placement_score=sum(c==q['answer'] for q,c in zip(PATHS['placement'],choices)),
                worlds=worlds,skipped=skip,est_hours=total,est_weeks=math.ceil(total/int(answers['hours'])))

@app.get('/api/onboarding')
def onboarding():
    return dict(questions=PATHS['questions'],placement=[public_q(q) for q in PATHS['placement']])

class Onboard(BaseModel):
    field:str
    experience:str
    goal:str
    hours:str
    support:str
    placement:list[int|None]=[]

@app.post('/api/onboarding')
def set_profile(body:Onboard):
    answers=body.model_dump(exclude={'placement'})
    for q in PATHS['questions']:
        if answers[q['id']] not in [o['value'] for o in q['options']]: raise HTTPException(422,f'Unknown answer for {q["id"]}')
    choices=body.placement if body.experience!='never' else []
    if body.experience!='never' and len(choices)!=len(PATHS['placement']): raise HTTPException(422,'Answer or skip every placement question')
    with LOCK:
        s=read();s['profile']=build_plan(answers,choices);active(s);save(s)
        return view(s)

@app.get('/api/export')
def export():
    with LOCK: return JSONResponse(read(),headers={'Content-Disposition':'attachment; filename="gauntlet-save.json"'})

app.mount('/static',StaticFiles(directory=ROOT/'static'),name='static')
@app.get('/')
def home(): return FileResponse(ROOT/'static/index.html',headers={'Cache-Control':'no-cache'})  # so new ?v= asset links are seen
