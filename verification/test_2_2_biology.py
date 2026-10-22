from verification.support import load
import pytest

def module():
    return load('world2/level_2_2_biology.py')

def test_post():
    from fastapi.testclient import TestClient
    c=TestClient(module().app)
    r=c.post("/samples",json={"name":"A","ph":7}); assert r.status_code==201; assert r.json()=={"name":"A","ph":7}
    for data in [{},{"name":"","ph":7},{"name":"A","ph":15},{"name":"A","ph":-1}]:
        assert c.post("/samples",json=data).status_code==422
