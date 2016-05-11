import pytest
from cif.router import Router


def test_router_basics():
    with Router() as r:
        assert r.handle_ping('1234', '')
