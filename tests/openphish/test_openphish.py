import py.test

from cif.smrt import Smrt
from cif.rule import Rule
from cif.constants import REMOTE
from pprint import pprint
import json

rule = 'rules/default/openphish.yml'
rule = Rule(path=rule)
rule.fetcher = 'file'
s = Smrt(REMOTE, 1234, client='dummy')


def test_spamhaus_drop():
    rule.feeds['urls']['remote'] = 'tests/openphish/feed.txt'
    x = s.process(rule, feed="urls")
    assert len(x) > 0
    x = json.loads(x[0])
    assert len(x['observable']) > 5