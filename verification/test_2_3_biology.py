from verification.support import load
import pytest

def module():
    return load('world2/level_2_3_biology.py')

def test_storage(tmp_path):
    import sqlite3
    p=str(tmp_path/"lab.db"); m=module()
    assert m.store_measurement(p,"S-101",3.3)==1
    assert m.store_measurement(p,"x'); DROP TABLE measurements;--",2)==2
    with sqlite3.connect(p) as c:
        rows=c.execute("SELECT name,value FROM measurements ORDER BY id").fetchall()
    assert rows[0]==("S-101",3.3); assert len(rows)==2
