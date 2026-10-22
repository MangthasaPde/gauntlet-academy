from verification.support import load
import pytest

def module():
    return load('world1/level_1_1_engineering.py')

@pytest.mark.parametrize("ident,value,flag,want", [("G-1",3.3,True,"G-1 | 3.30 bar | ONLINE"),("G-0",0,False,"G-0 | 0.00 bar | OFFLINE"),("VAC",-1.256,True,"VAC | -1.26 bar | ONLINE"),("G-9",12.999,False,"G-9 | 13.00 bar | OFFLINE")])
def test_label(ident,value,flag,want):
    assert module().format_gauge(ident,value,flag)==want
