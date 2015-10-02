import py.test

from cif.smrt import Smrt


def test_smrt():
    with Smrt() as s:
        assert type(s) is Smrt