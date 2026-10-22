from verification.support import load
import pytest

def module():
    return load('world2/level_2_2_science.py')

def test_post():
    from fastapi.testclient import TestClient
    c=TestClient(module().app)
    r=c.post("/solutions",json={"name":"A","concentration":2}); assert r.status_code==201; assert r.json()=={"name":"A","concentration":2}
    for data in [{},{"name":"","concentration":2},{"name":"A","concentration":6},{"name":"A","concentration":-1}]:
        assert c.post("/solutions",json=data).status_code==422
