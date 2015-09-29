import py.test

from cif.smrt import Smrt
from cif.rule import Rule
from cif.constants import REMOTE_ADDR
from pprint import pprint
import json

rule = 'rules/default/sans_edu.yml'
rule = Rule(path=rule)
rule.fetcher = 'file'
s = Smrt(REMOTE_ADDR, 1234, client='dummy')


def test_sans_low():
    feed = '02_domains_low'
    rule.feeds[feed]['remote'] = 'tests/sansedu/low.txt'
    x = s.process(rule, feed=feed)
    assert len(x) > 0

    x = json.loads(x[0])
    assert len(x['observable']) > 4


def test_sans_block():
    feed = 'block'
    rule.feeds[feed]['remote'] = 'tests/sansedu/block.txt'
    x = s.process(rule, feed=feed)
    assert len(x) > 0

    x = json.loads(x[0])

    pprint(x)
    assert len(x['observable']) > 4