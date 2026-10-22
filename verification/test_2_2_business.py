from verification.support import load
import pytest

def module():
    return load('world2/level_2_2_business.py')

def test_post():
    from fastapi.testclient import TestClient
    c=TestClient(module().app)
    r=c.post("/reviews",json={"name":"A","rating":4}); assert r.status_code==201; assert r.json()=={"name":"A","rating":4}
    for data in [{},{"name":"","rating":4},{"name":"A","rating":6},{"name":"A","rating":-1}]:
        assert c.post("/reviews",json=data).status_code==422
