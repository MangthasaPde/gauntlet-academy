from verification.support import load
import pytest

def module():
    return load('world1/level_1_3_cs.py')

def test_export():
    import json
    raw=json.dumps({"server":{"id":"A"},"requests":[{"latency":3},{"latency":5}],"extra":1})
    assert module().restructure_log(raw)=={"server_id":"A","latencies":[3,5],"average_latency":4}
def test_empty():
    assert module().restructure_log('{"server":{"id":"B"},"requests":[]}')=={"server_id":"B","latencies":[],"average_latency":None}
@pytest.mark.parametrize("raw", ['oops','{}','[]','{"server":{"id":""},"requests":[]}','{"server":{"id":"A"},"requests":[{"latency":"3"}]}','{"server":{"id":"A"},"requests":[{"latency":true}]}','{"server":{"id":"A"},"requests":null}'])
def test_bad_export(raw):
    with pytest.raises(ValueError): module().restructure_log(raw)
