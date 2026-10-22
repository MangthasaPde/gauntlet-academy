from verification.support import load
import pytest

def module():
    return load('world0/level_0_4.py')

@pytest.mark.parametrize("numbers,want", [([3,1,2],[3,4,6]),([],[]),([5],[5]),([2,-2,7],[2,0,7]),([0.5,0.25],[0.5,0.75])])
def test_running_total(numbers,want):
    original=numbers.copy()
    assert module().running_total(numbers)==want
    assert numbers==original, "Do not change the list you were given"
