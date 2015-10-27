import py.test

from cif.smrt import Smrt
from cif.rule import Rule
from cif.constants import REMOTE_ADDR
from pprint import pprint

rule = 'rules/default/spamhaus.yml'
rule = Rule(path=rule)
rule.fetcher = 'file'
s = Smrt(REMOTE_ADDR, 1234, client='dummy')


def test_spamhaus_drop():
    rule.feeds['drop']['remote'] = 'tests/spamhaus/drop.txt'
    x = s.process(rule, feed="drop")
    pprint(x)
    assert len(x) > 0


def test_spamhaus_edrop():
    rule.feeds['edrop']['remote'] = 'tests/spamhaus/edrop.txt'
    x = s.process(rule, feed="edrop")
    assert len(x) > 0