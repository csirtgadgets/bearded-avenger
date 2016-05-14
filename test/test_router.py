import pytest
from cif.router import Router


def test_router_basics():
    with Router() as r:
        pass
