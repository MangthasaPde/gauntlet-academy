from verification.support import load
import pytest

def module():
    return load('world2/level_2_1_biology.py')

def test_get():
    from fastapi.testclient import TestClient
    c=TestClient(module().app)
    for name in ["S-101","BLANK"]:
        r=c.get("/sample/"+name); assert r.status_code==200; assert r.json()=={"id":name,"concentration":3.3}
    assert c.get("/missing").status_code==404
