from verification.support import load
import pytest

def module():
    return load('world1/level_1_3_biology.py')

def test_export():
    import json
    raw=json.dumps({"sample":{"id":"A"},"measurements":[{"value":3},{"value":5}],"extra":1})
    assert module().restructure_results(raw)=={"sample_id":"A","values":[3,5],"average_value":4}
def test_empty():
    assert module().restructure_results('{"sample":{"id":"B"},"measurements":[]}')=={"sample_id":"B","values":[],"average_value":None}
@pytest.mark.parametrize("raw", ['oops','{}','[]','{"sample":{"id":""},"measurements":[]}','{"sample":{"id":"A"},"measurements":[{"value":"3"}]}','{"sample":{"id":"A"},"measurements":[{"value":true}]}','{"sample":{"id":"A"},"measurements":null}'])
def test_bad_export(raw):
    with pytest.raises(ValueError): module().restructure_results(raw)
