import py.test

from csirtg_smrt import Smrt
from csirtg_smrt.rule import Rule
from cifsdk.constants import REMOTE_ADDR
from pprint import pprint
import json

rule = 'rules/default/openphish.yml'
rule = Rule(path=rule)
rule.fetcher = 'file'
s = Smrt(REMOTE_ADDR, 1234, client='dummy')


def test_spamhaus_drop():
    rule.feeds['urls']['remote'] = 'test/openphish/feed.txt'
    x = s.process(rule, feed="urls")
    assert len(x) > 0
    assert len(x[0].indicator) > 4