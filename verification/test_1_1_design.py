from verification.support import load
import pytest

def module():
    return load('world1/level_1_1_design.py')

@pytest.mark.parametrize("ident,value,flag,want", [("logo",3.3,True,"logo | 3.30 px | VISIBLE"),("bg",0,False,"bg | 0.00 px | HIDDEN"),("shadow",-1.256,True,"shadow | -1.26 px | VISIBLE"),("title",12.999,False,"title | 13.00 px | HIDDEN")])
def test_label(ident,value,flag,want):
    assert module().format_layer(ident,value,flag)==want
