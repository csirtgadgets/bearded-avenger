import py.test

from cif.hunter import Hunter


def test_hunter():
    with Hunter() as h:
        assert isinstance(h, Hunter)
