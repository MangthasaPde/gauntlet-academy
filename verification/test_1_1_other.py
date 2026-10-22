from verification.support import load
import pytest

def module():
    return load('world1/level_1_1_other.py')

@pytest.mark.parametrize("ident,value,flag,want", [("Oslo",3.3,True,"Oslo | 3.30 °C | RAIN"),("Lima",0,False,"Lima | 0.00 °C | DRY"),("Riga",-1.256,True,"Riga | -1.26 °C | RAIN"),("Pune",12.999,False,"Pune | 13.00 °C | DRY")])
def test_label(ident,value,flag,want):
    assert module().format_weather(ident,value,flag)==want
