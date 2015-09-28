import py.test

from cif.smrt import Smrt
from cif.constants import REMOTE
from pprint import pprint

rule = 'rules/default/drg.yml'

def _smrt()
    return Smrt(REMOTE, 1234, client='dummy')

def test_drg_ssh():
    s = _smrt()
    x = s.process(rule, feed="ssh")
    assert len(x) > 0


def test_drg_vnc():
    s = _smrt()
    x = s.process(rule, feed="vnc")
    assert len(x) > 0