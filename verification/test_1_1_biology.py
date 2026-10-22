from verification.support import load
import pytest

def module():
    return load('world1/level_1_1_biology.py')

@pytest.mark.parametrize("sample,conc,done,want", [("S-101",3.3,True,"S-101 | 3.30 mg/L | ANALYSED"),("BLANK",0,False,"BLANK | 0.00 mg/L | PENDING"),("CTRL",-1.256,True,"CTRL | -1.26 mg/L | ANALYSED"),("S-9",12.999,False,"S-9 | 13.00 mg/L | PENDING")])
def test_sample_label(sample,conc,done,want):
    assert module().format_sample(sample,conc,done)==want
