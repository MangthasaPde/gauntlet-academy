from verification.support import load
import pytest

def module():
    return load('world1/level_1_3_other.py')

def test_export():
    import json
    raw=json.dumps({"trip":{"id":"A"},"stops":[{"distance":3},{"distance":5}],"extra":1})
    assert module().restructure_trip(raw)=={"trip_id":"A","distances":[3,5],"average_distance":4}
def test_empty():
    assert module().restructure_trip('{"trip":{"id":"B"},"stops":[]}')=={"trip_id":"B","distances":[],"average_distance":None}
@pytest.mark.parametrize("raw", ['oops','{}','[]','{"trip":{"id":""},"stops":[]}','{"trip":{"id":"A"},"stops":[{"distance":"3"}]}','{"trip":{"id":"A"},"stops":[{"distance":true}]}','{"trip":{"id":"A"},"stops":null}'])
def test_bad_export(raw):
    with pytest.raises(ValueError): module().restructure_trip(raw)
