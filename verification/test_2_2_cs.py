from verification.support import load
import pytest

def module():
    return load('world2/level_2_2_cs.py')

def test_post():
    from fastapi.testclient import TestClient
    c=TestClient(module().app)
    r=c.post("/servers",json={"name":"A","cpu":42}); assert r.status_code==201; assert r.json()=={"name":"A","cpu":42}
    for data in [{},{"name":"","cpu":42},{"name":"A","cpu":101},{"name":"A","cpu":-1}]:
        assert c.post("/servers",json=data).status_code==422
