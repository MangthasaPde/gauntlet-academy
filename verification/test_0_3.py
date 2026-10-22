from verification.support import load
import pytest

def module():
    return load('world0/level_0_3.py')

@pytest.mark.parametrize("score,want", [(100,"A"),(90,"A"),(89.5,"B"),(75,"B"),(74,"C"),(50,"C"),(49.9,"F"),(0,"F")])
def test_grades(score,want):
    assert module().grade(score)==want

@pytest.mark.parametrize("score", [-1,100.5,250])
def test_out_of_range(score):
    with pytest.raises(ValueError): module().grade(score)
