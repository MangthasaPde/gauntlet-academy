from verification.support import load
import pytest

def module():
    return load('world1/level_1_3_design.py')

def test_export():
    import json
    raw=json.dumps({"project":{"id":"A"},"images":[{"width":3},{"width":5}],"extra":1})
    assert module().restructure_project(raw)=={"project_id":"A","widths":[3,5],"average_width":4}
def test_empty():
    assert module().restructure_project('{"project":{"id":"B"},"images":[]}')=={"project_id":"B","widths":[],"average_width":None}
@pytest.mark.parametrize("raw", ['oops','{}','[]','{"project":{"id":""},"images":[]}','{"project":{"id":"A"},"images":[{"width":"3"}]}','{"project":{"id":"A"},"images":[{"width":true}]}','{"project":{"id":"A"},"images":null}'])
def test_bad_export(raw):
    with pytest.raises(ValueError): module().restructure_project(raw)
