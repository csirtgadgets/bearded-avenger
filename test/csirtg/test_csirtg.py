import py.test

from csirtg_smrt import Smrt
from csirtg_smrt.rule import Rule
from cifsdk.constants import REMOTE_ADDR
from pprint import pprint

rule = 'rules/default/csirtg.yml'
rule = Rule(path=rule)
rule.fetcher = 'file'

s = Smrt(REMOTE_ADDR, 1234, client='dummy')


def test_csirtg_portscanners():
    rule.feeds['port-scanners']['remote'] = 'test/csirtg/feed.txt'
    x = s.process(rule, feed="port-scanners")
    assert len(x) > 0

    ips = set()
    tags = set()

    for xx in x:
        ips.add(xx.indicator)
        tags.add(xx.tags[0])

    assert '109.111.134.64' in ips
    assert 'scanner' in tags