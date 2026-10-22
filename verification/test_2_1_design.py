from verification.support import load
import pytest

def module():
    return load('world2/level_2_1_design.py')

def test_get():
    from fastapi.testclient import TestClient
    c=TestClient(module().app)
    for name in ['ART-1', 'ART-2']:
        r=c.get("/artwork/"+name); assert r.status_code==200; assert r.json()=={"id":name,"aspect_ratio":1.5}
    assert c.get("/missing").status_code==404
