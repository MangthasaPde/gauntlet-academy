from verification.support import load
import pytest

def module():
    return load('world2/level_2_3_cs.py')

def test_storage(tmp_path):
    import sqlite3
    p=str(tmp_path/"ops.db"); m=module()
    assert m.store_event(p,"deploy",3.3)==1
    assert m.store_event(p,"x'); DROP TABLE events;--",2)==2
    with sqlite3.connect(p) as c:
        rows=c.execute("SELECT name,duration FROM events ORDER BY id").fetchall()
    assert rows[0]==("deploy",3.3); assert len(rows)==2
