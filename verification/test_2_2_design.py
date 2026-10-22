from verification.support import load
import pytest

def module():
    return load('world2/level_2_2_design.py')

def test_post():
    from fastapi.testclient import TestClient
    c=TestClient(module().app)
    r=c.post("/colors",json={"name":"A","opacity":0.5}); assert r.status_code==201; assert r.json()=={"name":"A","opacity":0.5}
    for data in [{},{"name":"","opacity":0.5},{"name":"A","opacity":2},{"name":"A","opacity":-1}]:
        assert c.post("/colors",json=data).status_code==422
