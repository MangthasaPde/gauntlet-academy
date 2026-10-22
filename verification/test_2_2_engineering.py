from verification.support import load
import pytest

def module():
    return load('world2/level_2_2_engineering.py')

def test_post():
    from fastapi.testclient import TestClient
    c=TestClient(module().app)
    r=c.post("/parts",json={"name":"A","tolerance":2}); assert r.status_code==201; assert r.json()=={"name":"A","tolerance":2}
    for data in [{},{"name":"","tolerance":2},{"name":"A","tolerance":6},{"name":"A","tolerance":-1}]:
        assert c.post("/parts",json=data).status_code==422
