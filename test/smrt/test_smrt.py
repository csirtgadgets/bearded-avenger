import py.test

from cif.smrt import Smrt
from cif.constants import REMOTE_ADDR
from pprint import pprint


def test_smrt():
    with Smrt(REMOTE_ADDR, 1234, client='dummy') as s:
        assert type(s) is Smrt

        x = s.process('test/smrt/rules')
        assert len(x) > 0

        x = s.process('test/smrt/rules/csirtg.yml')
        assert len(x) > 0

        x = s.process('test/smrt/rules/csirtg.yml', feed='port-scanners')
        assert len(x) > 0

        x = s.process('test/smrt/rules/csirtg.yml', feed='port-scanners2')
        assert len(x) == 0