from verification.support import load
import pytest

def module():
    return load('world2/level_2_1_engineering.py')

def test_get():
    from fastapi.testclient import TestClient
    c=TestClient(module().app)
    for name in ['G-1', 'G-2']:
        r=c.get("/gauge/"+name); assert r.status_code==200; assert r.json()=={"id":name,"pressure":3.3}
    assert c.get("/missing").status_code==404
