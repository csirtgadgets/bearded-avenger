import py.test

from cif.smrt import Smrt
from cif.rule import Rule
from cif.constants import REMOTE_ADDR
from pprint import pprint

rule = 'rules/default/drg.yml'
rule = Rule(path=rule)
rule.fetcher = 'file'

s = Smrt(REMOTE_ADDR, 1234, client='dummy')


def test_drg_ssh():
    rule.feeds['ssh']['remote'] = 'test/drg/feed.txt'
    x = s.process(rule, feed="ssh")
    assert len(x) > 0


def test_drg_vnc():
    rule.feeds['vnc']['remote'] = 'test/drg/feed.txt'
    x = s.process(rule, feed="vnc")
    assert len(x) > 0
