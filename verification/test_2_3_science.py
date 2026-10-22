from verification.support import load
import pytest

def module():
    return load('world2/level_2_3_science.py')

def test_storage(tmp_path):
    import sqlite3
    p=str(tmp_path/"lab.db"); m=module()
    assert m.store_result(p,"Trial-1",3.3)==1
    assert m.store_result(p,"x'); DROP TABLE results;--",2)==2
    with sqlite3.connect(p) as c:
        rows=c.execute("SELECT name,value FROM results ORDER BY id").fetchall()
    assert rows[0]==("Trial-1",3.3); assert len(rows)==2
