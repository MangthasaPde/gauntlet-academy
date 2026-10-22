from verification.support import load
import pytest

def module():
    return load('world2/level_2_1_business.py')

def test_get():
    from fastapi.testclient import TestClient
    c=TestClient(module().app)
    for name in ["SKU-1","SKU-2"]:
        r=c.get("/product/"+name); assert r.status_code==200; assert r.json()=={"id":name,"price":19.99}
    assert c.get("/missing").status_code==404
