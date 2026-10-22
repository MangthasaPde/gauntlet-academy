from verification.support import load
import pytest

def module():
    return load('world1/level_1_3_business.py')

def test_order():
    import json
    raw=json.dumps({"order":{"id":"A"},"items":[{"price":3},{"price":5}],"extra":1})
    assert module().restructure_order(raw)=={"order_id":"A","prices":[3,5],"average_price":4}
def test_empty():
    assert module().restructure_order('{"order":{"id":"B"},"items":[]}')=={"order_id":"B","prices":[],"average_price":None}
@pytest.mark.parametrize("raw", ['oops','{}','[]','{"order":{"id":""},"items":[]}','{"order":{"id":"A"},"items":[{"price":"3"}]}','{"order":{"id":"A"},"items":[{"price":true}]}','{"order":{"id":"A"},"items":null}'])
def test_bad_order(raw):
    with pytest.raises(ValueError): module().restructure_order(raw)
