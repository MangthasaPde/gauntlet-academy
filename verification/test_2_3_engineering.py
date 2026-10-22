from verification.support import load
import pytest

def module():
    return load('world2/level_2_3_engineering.py')

def test_storage(tmp_path):
    import sqlite3
    p=str(tmp_path/"site.db"); m=module()
    assert m.store_inspection(p,"Pier-1",3.3)==1
    assert m.store_inspection(p,"x'); DROP TABLE inspections;--",2)==2
    with sqlite3.connect(p) as c:
        rows=c.execute("SELECT name,strain FROM inspections ORDER BY id").fetchall()
    assert rows[0]==("Pier-1",3.3); assert len(rows)==2
