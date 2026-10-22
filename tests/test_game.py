import json
import math
import os
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from app import main as game

@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setattr(game,'DATA',tmp_path/'data');game.DATA.mkdir()
    monkeypatch.setattr(game,'WORK',tmp_path/'workspace');game.WORK.mkdir()
    monkeypatch.setattr(game,'BUSY',False)
    return TestClient(game.app,headers={'X-Gauntlet':'local'})

def learn(client,id):
    r=client.post('/api/lesson/complete',json={'id':id});assert r.status_code==200,r.text

def trial(client,kind='level',target='1.1',wrong=()):
    if kind=='level': learn(client,target)
    r=client.post('/api/quiz/start',json={'kind':kind,'target':target});assert r.status_code==200,r.text
    t=r.json()
    for i in range(t['total']):
        private=game.read()['session'];q=private['questions'][i]
        choice=(q['answer']+1)%4 if i in wrong else q['answer']
        r=client.post('/api/quiz/answer',json={'session_id':t['id'],'index':i,'choice':choice})
        assert r.status_code==200,r.text
    return r.json()['state']

def test_locks_and_no_answer_leak(client):
    assert client.get('/').status_code==200
    assert client.post('/api/initialize',json={'id':'1.1'}).status_code==403
    assert client.post('/api/quiz/start',json={'kind':'level','target':'1.2'}).status_code==403
    assert client.post('/api/quiz/start',json={'kind':'gate','target':'1'}).status_code==403
    data=client.get('/api/curriculum').json()
    assert 'quiz' not in data['items'][0]
    assert client.post('/api/quiz/start',json={'kind':'level','target':'1.1'}).status_code==403
    assert client.post('/api/lesson/complete',json={'id':'1.2'}).status_code==403
    learn(client,'1.1');assert client.get('/api/curriculum').json()['items'][0]['lesson_done']
    r=client.post('/api/quiz/start',json={'kind':'level','target':'1.1'}).json()
    assert 'answer' not in r['question'] and 'explanation' not in r['question']

def test_mistakes_retry_and_duplicate_answers(client):
    s=trial(client,wrong=(0,));assert s['hp']==90 and '1.1' not in s['quiz_passed']
    s=trial(client);assert s['xp']==30 and s['combos']['1.1']==1.5
    assert trial(client)['xp']==30
    t=game.read()['session']
    assert client.post('/api/quiz/answer',json={'session_id':t['id'],'index':2,'choice':0}).status_code==409

def test_initialize_preserves_work_and_real_verification(client):
    trial(client)
    r=client.post('/api/initialize',json={'id':'1.1'});assert r.status_code==200
    p=Path(r.json()['path'])
    bad=client.post('/api/verify',json={'id':'1.1'}).json();assert not bad['passed']
    p.write_text('def format_telemetry(sensor_id,voltage,active):\n    status="ON" if active else "OFF"\n    return f"{sensor_id} | {voltage:.2f} V | {status}"\n')
    original=p.read_text();client.post('/api/initialize',json={'id':'1.1'});assert p.read_text()==original
    result=client.post('/api/verify',json={'id':'1.1'}).json()
    assert result['passed'],result['output']
    assert result['reward']==150
    assert client.post('/api/verify',json={'id':'1.1'}).json()['reward']==0
    assert client.get('/api/curriculum').json()['items'][1]['unlocked']

def test_gate_key_and_world_unlock(client,monkeypatch):
    s=game.read();s['completed']=[f'1.{n}' for n in range(1,5)];game.save(s)
    state=trial(client,'gate','1',wrong=(0,1));assert '1' in state['keys']
    assert client.post('/api/initialize',json={'id':'1.boss'}).status_code==200
    monkeypatch.setattr(game,'run_verification',lambda id:(True,'all tests pass'))
    r=client.post('/api/verify',json={'id':'1.boss'}).json()
    assert r['reward']==300 and r['state']['boss_hp']['1']==0
    learn(client,'2.1')
    assert client.post('/api/quiz/start',json={'kind':'level','target':'2.1'}).status_code==200

def test_old_save_counts_passed_quiz_as_lesson(client):
    s=game.initial();del s['lessons_read'];s['quiz_passed']=['1.1'];game.save(s)
    assert game.read()['lessons_read']==[]
    assert client.post('/api/quiz/start',json={'kind':'level','target':'1.1'}).status_code==200

def test_daily_reward_and_death_recovery(client):
    assert client.post('/api/quiz/start',json={'kind':'daily'}).status_code==403
    s=game.read();s['completed']=['1.1'];game.save(s)
    assert trial(client,'daily','')['xp']==50
    assert trial(client,'daily','')['xp']==50
    s=game.read();s['hp']=0;game.save(s)
    assert client.post('/api/quiz/start',json={'kind':'daily'}).status_code==409
    assert client.post('/api/recover',json={}).json()['hp']==100
    assert game.read()['xp']==50

def test_timer_origin_and_persistence(client):
    learn(client,'1.1')
    t=client.post('/api/quiz/start',json={'kind':'level','target':'1.1','timed':True}).json()
    s=game.read();s['session']['deadline']=1;game.save(s)
    assert client.post('/api/quiz/answer',json={'session_id':t['id'],'index':0,'choice':0}).status_code==409
    assert client.post('/api/recover',json={},headers={'Origin':'https://evil.example'}).status_code==403
    assert TestClient(game.app).post('/api/recover',json={}).status_code==403
    assert client.get('/api/export').json()['session']['finished']
    assert client.get('/api/state').json()['hp']==100

def test_content_complete():
    assert len(game.CUR['levels'])==20 and len(game.BOSSES)==4
    assert sorted(game.PATHS['levels'])==sorted(l['id'] for l in game.CUR['levels'])
    for level in game.CUR['levels']:
        assert len(level['quiz'])==3
        assert len(level['quiz'][0]['code'].splitlines())==4
        assert [q['kind'] for q in level['quiz']][:2]==['Predict the Output','Spot the Bug']
        for q in level['quiz']: assert len(q['options'])==4 and 0<=q['answer']<4
    for w,questions in game.CUR['gatekeepers'].items(): assert len(questions)==10
    for level in game.CUR['levels']:
        pages=game.LESSONS[level['id']]['pages'];assert len(pages)>=4
        assert any(p.get('type')=='check' for p in pages)
        for p in pages:
            if p.get('type')=='check': assert 0<=p['answer']<len(p['options']) and p['explain']
            else: assert p['title'] and p['body']
    for id,item in game.ITEMS.items():
        assert (game.ROOT/'templates'/item['path']).is_file()
        assert (game.ROOT/'verification'/('test_'+id.replace('.','_')+'.py')).is_file()

def onboard(client,experience='comfortable',goal='ai_engineer',right=0,hours='5',field='science'):
    # Answer the first `right` placement questions correctly and skip the rest.
    placement=[q['answer'] if i<right else None for i,q in enumerate(game.PATHS['placement'])]
    r=client.post('/api/onboarding',json=dict(field=field,experience=experience,goal=goal,hours=hours,support='hints',placement=placement))
    assert r.status_code==200,r.text
    return r.json()

def test_onboarding_questions_hide_answers(client):
    data=client.get('/api/onboarding').json()
    assert [q['id'] for q in data['questions']]==['field','experience','goal','hours','support']
    assert data['placement'] and all('answer' not in q for q in data['placement'])
    assert client.get('/api/state').json()['profile'] is None

def test_onboarding_validates_answers(client):
    bad=dict(field='science',experience='comfortable',goal='world_domination',hours='5',support='hints',placement=[None]*6)
    assert client.post('/api/onboarding',json=bad).status_code==422
    short=dict(bad,goal='code',placement=[0])
    assert client.post('/api/onboarding',json=short).status_code==422
    assert client.post('/api/onboarding',json=dict(short,experience='never',placement=[])).status_code==200

def test_placement_tiers():
    tier=lambda right,exp='little':game.placement_tier(exp,[q['answer'] if i<right else None for i,q in enumerate(game.PATHS['placement'])])
    assert tier(6,'never')=='beginner'
    assert tier(0)=='beginner' and tier(2)=='beginner'
    assert tier(3)=='intermediate' and tier(4)=='intermediate'
    assert tier(5)=='advanced' and tier(6)=='advanced'

def test_new_coders_start_in_boot_camp(client,monkeypatch):
    s=onboard(client,experience='never')
    assert s['profile']['tier']=='beginner' and s['profile']['skipped']==[]
    assert s['path_worlds']==[0,1,2,3,4] and s['open_worlds']==[0] and s['current_world']==0
    assert client.post('/api/lesson/complete',json={'id':'1.1'}).status_code==403
    # Finishing Boot Camp opens Room 1 and earns a badge.
    s=game.read();s['completed']=['0.1','0.2','0.3'];game.save(s)
    trial(client,target='0.4')
    client.post('/api/initialize',json={'id':'0.4'})
    monkeypatch.setattr(game,'run_verification',lambda id:(True,'ok'))
    s=client.post('/api/verify',json={'id':'0.4'}).json()['state']
    assert s['open_worlds']==[0,1] and s['current_world']==1 and 'Boot Camp Graduate' in s['badges']
    learn(client,'1.1')

def test_boot_camp_placement_rules(client):
    assert onboard(client,experience='little')['path_worlds'][0]==0
    assert onboard(client,experience='little',right=3)['path_worlds']==[1,2,3,4]
    assert onboard(client,experience='comfortable')['path_worlds']==[1,2,3,4]
    # Boot Camp stays open to everyone and never blocks Room 1 when it is off the path.
    s=client.get('/api/state').json();assert s['open_worlds']==[0,1]
    learn(client,'0.1')

def test_intermediate_places_out_of_basics(client):
    s=onboard(client,right=3)
    assert s['profile']['skipped']==['1.1','1.2','1.3']
    items={x['id']:x for x in client.get('/api/curriculum').json()['items']}
    assert items['1.4']['unlocked'] and not items['2.1']['unlocked']
    # Placed-out missions count toward the checkpoint but are not marked as built.
    s=game.read();s['completed']=['1.4'];game.save(s)
    assert client.post('/api/quiz/start',json={'kind':'gate','target':'1'}).status_code==200
    assert game.read()['completed']==['1.4']

def test_advanced_skips_whole_rooms_but_keeps_final_project(client):
    s=onboard(client,right=6)
    p=s['profile']
    assert '1.boss' in p['skipped'] and '2.boss' not in p['skipped'] and '2.4' not in p['skipped']
    assert s['open_worlds']==[0,1,2] and s['current_world']==2
    items={x['id']:x for x in client.get('/api/curriculum').json()['items']}
    assert items['2.4']['unlocked'] and items['1.boss']['unlocked']
    # Learning to code only: everything is placed out except the room project.
    p=onboard(client,right=6,goal='code')['profile']
    assert '1.boss' not in p['skipped'] and p['est_hours']==5.5

def test_goal_path_opens_rooms_off_the_path(client):
    s=onboard(client,experience='never',goal='ai_apps',hours='2')
    assert s['path_worlds']==[0,1,3] and s['open_worlds']==[0]
    assert s['profile']['est_weeks']==math.ceil((12*2+2*5.5)/2)
    st=game.read();st['bosses']=['1'];st['completed']=['0.1','0.2','0.3','0.4'];game.save(st)
    s=client.get('/api/state').json()
    assert s['open_worlds']==[0,1,2,3] and s['current_world']==3
    learn(client,'3.1')
    assert client.post('/api/quiz/start',json={'kind':'level','target':'3.1'}).status_code==200

def test_retaking_onboarding_keeps_progress(client):
    onboard(client,right=6)
    s=game.read();s['completed']=['2.4'];s['xp']=150;game.save(s)
    s=onboard(client,experience='never')
    assert s['profile']['skipped']==[] and s['completed']==['2.4'] and s['xp']==150

def test_beginners_lose_less_health(client):
    assert client.get('/api/state').json()['penalty']==10
    onboard(client,experience='never')
    s=trial(client,target='0.1',wrong=(0,));assert s['penalty']==5 and s['hp']==95
    onboard(client,right=3)
    s=trial(client,target='1.4',wrong=(0,));assert s['hp']==85

def test_challenge_skips_quiz_without_bonus(client,monkeypatch):
    onboard(client,right=3)
    assert client.post('/api/initialize',json={'id':'1.4'}).status_code==403
    assert client.post('/api/challenge',json={'id':'2.1'}).status_code==403
    assert client.post('/api/challenge',json={'id':'1.boss'}).status_code==403
    s=client.post('/api/challenge',json={'id':'1.4'}).json();assert s['challenges']==['1.4']
    assert client.post('/api/initialize',json={'id':'1.4'}).status_code==200
    monkeypatch.setattr(game,'run_verification',lambda id:(True,'all tests pass'))
    r=client.post('/api/verify',json={'id':'1.4'}).json()
    assert r['passed'] and r['reward']==100
    # With 1.1-1.3 placed out and 1.4 built by challenge, the checkpoint opens.
    assert client.post('/api/quiz/start',json={'kind':'gate','target':'1'}).status_code==200

# ---------------------------------------------------------------- field examples

def own_starters():
    """Missions with a starter file of their own: Boot Camp, plus every variant mission of every field."""
    cases=[(f'0.{n}',None) for n in range(1,5)]
    for field,overlay in sorted(game.FIELDS.items()):
        cases+=[(id,field) for id,level in sorted(overlay['levels'].items()) if level.get('variant')]
    return cases

def play_to(client,id,field):
    """Put a player from `field` in front of mission `id`, skipping its lesson and quiz."""
    if field: onboard(client,field=field)
    s=game.read();world=int(id[0])
    s['challenges']=[id];s['completed']=[f'{world}.{n}' for n in range(1,int(id[2]))]
    s['bosses']=[str(w) for w in range(1,world)]
    game.save(s)

def mission(client,id):
    return next(x for x in client.get('/api/curriculum').json()['items'] if x['id']==id)

@pytest.mark.parametrize("id,field",own_starters())
def test_own_starters_fail_their_own_tests(client,id,field):
    play_to(client,id,field)
    path=Path(client.post('/api/initialize',json={'id':id}).json()['path'])
    result=client.post('/api/verify',json={'id':id}).json()
    suffix=f'_{field}' if field else ''
    assert path.name==f"level_{id.replace('.','_')}{suffix}.py"
    assert not result['passed'], 'The starter file must fail its tests'
    assert f"test_{id.replace('.','_')}{suffix}.py" in result['output'], 'The tests for this field must be the ones that ran'

# Reference solutions are not shipped. Point GAUNTLET_SOLUTIONS at a folder of <id>.py / <id>_<field>.py files to run them.
SOLUTIONS=os.environ.get('GAUNTLET_SOLUTIONS')

@pytest.mark.skipif(not SOLUTIONS,reason='set GAUNTLET_SOLUTIONS to a folder of reference solutions')
@pytest.mark.parametrize("id,field",own_starters())
def test_reference_solutions_pass(client,id,field):
    play_to(client,id,field)
    path=Path(client.post('/api/initialize',json={'id':id}).json()['path'])
    path.write_text((Path(SOLUTIONS)/(f'{id}_{field}.py' if field else f'{id}.py')).read_text())
    result=client.post('/api/verify',json={'id':id}).json()
    assert result['passed'],result['output']

def test_field_overlays_are_valid():
    options={o['value'] for q in game.PATHS['questions'] if q['id']=='field' for o in q['options']}
    # Electronics is the original wording; every other field answer has examples of its own.
    assert set(game.FIELDS)==options-{'ece'}
    for field,overlay in game.FIELDS.items():
        assert field in options
        for id,level in overlay['levels'].items():
            base=game.ITEMS[id];pages=game.LESSONS[id]['pages']
            for i,p in level.get('pages',{}).items():
                assert int(i)<len(pages) and (p.get('type')=='check')==(pages[int(i)].get('type')=='check'),(id,i)
                if p.get('type')=='check': assert 0<=p['answer']<len(p['options']) and p['explain']
                else: assert p['title'] and p['body']
            for i,q in level.get('quiz',{}).items():
                assert q['kind']==base['quiz'][int(i)]['kind'] and len(q['options'])==4 and 0<=q['answer']<4,(id,i)
                if int(i)==0: assert len(q['code'].splitlines())==4,(id,i)
            if level.get('variant'):
                rel=Path(base['path']);variant=rel.with_name(rel.stem+f'_{field}.py')
                template=game.ROOT/'templates'/variant
                assert template.is_file() and (game.ROOT/'verification'/f"test_{id.replace('.','_')}_{field}.py").is_file()
                mission_page=json.dumps(level['pages'][str(len(pages)-1)])
                for token in level['contract']: assert token in level['quest'] and token in mission_page,(id,token)
                import re
                for name in re.findall(r'^(?:async )?def (\w+)',template.read_text(),re.M): assert name in level['quest'],(id,name)
        for world,items in overlay.get('gatekeepers',{}).items():
            for i,q in items.items():
                assert q['kind']==game.CUR['gatekeepers'][world][int(i)]['kind'] and len(q['options'])==4 and 0<=q['answer']<4

def test_players_see_their_own_field(client):
    assert 'format_telemetry' in mission(client,'1.1')['quest'] and not client.get('/api/state').json()['field_examples']
    s=onboard(client,field='biology');assert s['field_examples']
    m=mission(client,'1.1')
    assert 'format_sample' in m['quest'] and m['title']=='Lab Notebook: Sample Labels' and m['path'].endswith('level_1_1_biology.py')
    assert 'concentration' in m['lesson_pages'][0]['code'] and 'mg/L' in m['lesson_pages'][6]['code']
    assert 'format_invoice' in (onboard(client,field='business'),mission(client,'1.1'))[1]['quest']
    assert 'format_layer' in (onboard(client,field='design'),mission(client,'1.1'))[1]['quest']
    # Electronics keeps the original missions.
    s=onboard(client,field='ece');assert not s['field_examples']
    assert 'format_telemetry' in mission(client,'1.1')['quest'] and mission(client,'1.1')['path'].endswith('level_1_1.py')

def test_field_quiz_and_checkpoint_questions(client):
    onboard(client,field='biology');learn(client,'1.1')
    t=client.post('/api/quiz/start',json={'kind':'level','target':'1.1'}).json()
    assert 'mg/L' in t['question']['code'] or 'conc' in t['question']['code']
    s=game.read();s['completed']=[f'1.{n}' for n in range(1,5)];game.save(s)
    client.post('/api/quiz/start',json={'kind':'gate','target':'1'})
    questions=game.read()['session']['questions']
    assert 'mg/L' in questions[0]['code'] and 'volts' not in json.dumps(questions)
    onboard(client,field='ece');client.post('/api/quiz/start',json={'kind':'gate','target':'1'})
    assert 'volts' in game.read()['session']['questions'][0]['code']

def test_switching_field_keeps_progress(client,monkeypatch):
    play_to(client,'1.1','biology');client.post('/api/initialize',json={'id':'1.1'})
    monkeypatch.setattr(game,'run_verification',lambda id:(True,'ok'))
    assert client.post('/api/verify',json={'id':'1.1'}).json()['passed']
    s=onboard(client,field='business')
    assert '1.1' in s['completed'] and mission(client,'1.1')['path'].endswith('level_1_1_business.py')
