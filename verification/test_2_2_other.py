from verification.support import load
import pytest

def module():
    return load('world2/level_2_2_other.py')

def test_post():
    from fastapi.testclient import TestClient
    c=TestClient(module().app)
    r=c.post("/habits",json={"name":"A","hours":2}); assert r.status_code==201; assert r.json()=={"name":"A","hours":2}
    for data in [{},{"name":"","hours":2},{"name":"A","hours":25},{"name":"A","hours":-1}]:
        assert c.post("/habits",json=data).status_code==422
