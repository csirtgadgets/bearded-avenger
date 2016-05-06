import pytest
import json
from cif.router import Router


def test_router_ping():
    with Router() as router:
        x = router.handle_ping('1234', 'ping')
        assert len(x) > 0

        x = json.loads(x)
        assert x['status'] == 'success'