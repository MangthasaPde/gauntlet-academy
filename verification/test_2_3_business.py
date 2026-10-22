from verification.support import load
import pytest

def module():
    return load('world2/level_2_3_business.py')

def test_storage(tmp_path):
    import sqlite3
    p=str(tmp_path/"shop.db"); m=module()
    assert m.store_sale(p,"Mug",12.5)==1
    assert m.store_sale(p,"x'); DROP TABLE sales;--",2)==2
    with sqlite3.connect(p) as c:
        rows=c.execute("SELECT product,amount FROM sales ORDER BY id").fetchall()
    assert rows[0]==("Mug",12.5); assert len(rows)==2
