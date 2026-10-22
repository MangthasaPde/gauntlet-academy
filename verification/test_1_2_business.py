from verification.support import load
import pytest

def module():
    return load('world1/level_1_2_business.py')

@pytest.mark.parametrize("prices,lo,hi,want", [([-3,0,2,5,8],0,5,[0,2,5]),([],0,1,[]),([2,2,1],2,2,[2,2]),([-2,-1,0],-2,-1,[-2,-1])])
def test_filter(prices,lo,hi,want):
    original=prices.copy()
    assert module().filter_prices(prices,lo,hi)==want
    assert prices==original, "Do not mutate the input prices"
def test_invalid_range():
    with pytest.raises(ValueError): module().filter_prices([1],5,1)
