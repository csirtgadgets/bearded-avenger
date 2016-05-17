import py.test

from csirtg_smrt import Smrt
from csirtg_smrt.rule import Rule
from cifsdk.constants import REMOTE_ADDR
from pprint import pprint

rule = 'rules/default/vxvault.yml'
rule = Rule(path=rule)
rule.fetcher = 'file'

s = Smrt(REMOTE_ADDR, 1234, client='dummy')


def test_vxvault_urls():
    rule.feeds['urls']['remote'] = 'test/vxvault/feed.txt'
    x = s.process(rule, feed="urls")
    assert len(x) > 0

    urls = set()
    tags = set()

    for xx in x:
        urls.add(xx.indicator)
        tags.add(xx.tags[0])

    assert 'http://jeansowghtqq.com/85.exe' in urls
    assert 'malware' in tags