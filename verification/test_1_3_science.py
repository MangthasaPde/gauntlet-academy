from verification.support import load
import pytest

def module():
    return load('world1/level_1_3_science.py')

def test_export():
    import json
    raw=json.dumps({"experiment":{"id":"A"},"trials":[{"result":3},{"result":5}],"extra":1})
    assert module().restructure_experiment(raw)=={"experiment_id":"A","results":[3,5],"average_result":4}
def test_empty():
    assert module().restructure_experiment('{"experiment":{"id":"B"},"trials":[]}')=={"experiment_id":"B","results":[],"average_result":None}
@pytest.mark.parametrize("raw", ['oops','{}','[]','{"experiment":{"id":""},"trials":[]}','{"experiment":{"id":"A"},"trials":[{"result":"3"}]}','{"experiment":{"id":"A"},"trials":[{"result":true}]}','{"experiment":{"id":"A"},"trials":null}'])
def test_bad_export(raw):
    with pytest.raises(ValueError): module().restructure_experiment(raw)
