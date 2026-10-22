from verification.support import load
import pytest

def module():
    return load('world2/level_2_1_science.py')

def test_get():
    from fastapi.testclient import TestClient
    c=TestClient(module().app)
    for name in ['EXP-1', 'EXP-2']:
        r=c.get("/experiment/"+name); assert r.status_code==200; assert r.json()=={"id":name,"temperature":21.5}
    assert c.get("/missing").status_code==404
