import pytest
import json
from cif.router import Router

@pytest.yield_fixture
def running_router():
    with Router() as router:
        yield router


def test_router_ping(running_router):
    x = running_router.handle_ping('1234', 'ping')
    assert len(x) > 0

    x = json.loads(x)
    assert x['status'] == 'success'
