from verification.support import load
import pytest

def module():
    return load('world2/level_2_3_other.py')

def test_storage(tmp_path):
    import sqlite3
    p=str(tmp_path/"budget.db"); m=module()
    assert m.store_expense(p,"Coffee",3.3)==1
    assert m.store_expense(p,"x'); DROP TABLE expenses;--",2)==2
    with sqlite3.connect(p) as c:
        rows=c.execute("SELECT item,cost FROM expenses ORDER BY id").fetchall()
    assert rows[0]==("Coffee",3.3); assert len(rows)==2
