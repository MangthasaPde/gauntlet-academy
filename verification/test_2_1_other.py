from verification.support import load
import pytest

def module():
    return load('world2/level_2_1_other.py')

def test_get():
    from fastapi.testclient import TestClient
    c=TestClient(module().app)
    for name in ['Oslo', 'Lima']:
        r=c.get("/city/"+name); assert r.status_code==200; assert r.json()=={"id":name,"temperature":18.5}
    assert c.get("/missing").status_code==404
