from verification.support import load
import pytest

def module():
    return load('world1/level_1_1_cs.py')

@pytest.mark.parametrize("ident,value,flag,want", [("web-1",3.3,True,"web-1 | 3.30 ms | SYNCED"),("db",0,False,"db | 0.00 ms | DRIFTING"),("cache",-1.256,True,"cache | -1.26 ms | SYNCED"),("api",12.999,False,"api | 13.00 ms | DRIFTING")])
def test_label(ident,value,flag,want):
    assert module().format_clock(ident,value,flag)==want
