from verification.support import load
import pytest

def module():
    return load('world0/level_0_2.py')

@pytest.mark.parametrize("total,people,tip,want", [(100,4,0,25.0),(100,4,10,27.5),(50,3,0,16.67),(0,2,15,0.0),(80,1,12.5,90.0)])
def test_split(total,people,tip,want):
    assert module().split_bill(total,people,tip)==want

@pytest.mark.parametrize("people", [0,-2])
def test_needs_people(people):
    with pytest.raises(ValueError): module().split_bill(10,people,0)
