from verification.support import load
import pytest

def module():
    return load('world1/level_1_1_science.py')

@pytest.mark.parametrize("ident,value,flag,want", [("T-1",3.3,True,"T-1 | 3.30 °C | CALIBRATED"),("ICE",0,False,"ICE | 0.00 °C | UNCALIBRATED"),("COLD",-1.256,True,"COLD | -1.26 °C | CALIBRATED"),("T-9",12.999,False,"T-9 | 13.00 °C | UNCALIBRATED")])
def test_label(ident,value,flag,want):
    assert module().format_measurement(ident,value,flag)==want
