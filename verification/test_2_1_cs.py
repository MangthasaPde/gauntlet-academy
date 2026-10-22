from verification.support import load
import pytest

def module():
    return load('world2/level_2_1_cs.py')

def test_get():
    from fastapi.testclient import TestClient
    c=TestClient(module().app)
    for name in ['web-1', 'db-2']:
        r=c.get("/server/"+name); assert r.status_code==200; assert r.json()=={"id":name,"latency":3.3}
    assert c.get("/missing").status_code==404
