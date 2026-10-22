from verification.support import load
import pytest

def module():
    return load('world2/level_2_3_design.py')

def test_storage(tmp_path):
    import sqlite3
    p=str(tmp_path/"studio.db"); m=module()
    assert m.store_asset(p,"hero.png",3.3)==1
    assert m.store_asset(p,"x'); DROP TABLE assets;--",2)==2
    with sqlite3.connect(p) as c:
        rows=c.execute("SELECT name,size FROM assets ORDER BY id").fetchall()
    assert rows[0]==("hero.png",3.3); assert len(rows)==2
