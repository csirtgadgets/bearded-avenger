import pytest
from cif.router import Router


def test_router_basics():
    with Router(test=True) as r:
        pass
