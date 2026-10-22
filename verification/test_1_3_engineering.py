from verification.support import load
import pytest

def module():
    return load('world1/level_1_3_engineering.py')

def test_export():
    import json
    raw=json.dumps({"bridge":{"id":"A"},"strains":[{"strain":3},{"strain":5}],"extra":1})
    assert module().restructure_inspection(raw)=={"bridge_id":"A","strains":[3,5],"average_strain":4}
def test_empty():
    assert module().restructure_inspection('{"bridge":{"id":"B"},"strains":[]}')=={"bridge_id":"B","strains":[],"average_strain":None}
@pytest.mark.parametrize("raw", ['oops','{}','[]','{"bridge":{"id":""},"strains":[]}','{"bridge":{"id":"A"},"strains":[{"strain":"3"}]}','{"bridge":{"id":"A"},"strains":[{"strain":true}]}','{"bridge":{"id":"A"},"strains":null}'])
def test_bad_export(raw):
    with pytest.raises(ValueError): module().restructure_inspection(raw)
