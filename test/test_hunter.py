import pytest

from cif.hunter import Hunter
from zmq import Context


def test_hunter():
    with Hunter(Context.instance()) as h:
        assert isinstance(h, Hunter)
