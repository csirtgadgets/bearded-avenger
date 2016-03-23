import py.test

from cif.smrt import Smrt
from cif.rule import Rule
from cif.constants import REMOTE_ADDR
from pprint import pprint

rule = 'rules/default/ransomware_abuse_ch.yml'
rule = Rule(path=rule)
rule.fetcher = 'file'

s = Smrt(REMOTE_ADDR, 1234, client='dummy')


def test_abuse_ch_ransomware():
    rule.feeds['ransomware']['remote'] = 'test/ransomware_abuse_ch/feed.txt'
    x = s.process(rule, feed="ransomware")
    assert len(x) > 0

    indicators = set()
    tags = set()

    for xx in x:
        indicators.add(xx.indicator)
        tags.add(xx.tags[0])

    assert 'http://grandaareyoucc.asia/85.exe' in indicators
    assert 'botnet' in tags