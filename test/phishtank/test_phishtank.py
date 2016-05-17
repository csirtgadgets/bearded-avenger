import py.test

from csirtg_smrt import Smrt
from csirtg_smrt.rule import Rule
from cifsdk.constants import REMOTE_ADDR
from pprint import pprint

rule = 'rules/default/phishtank.yml'
rule = Rule(path=rule)
rule.fetcher = 'file'
s = Smrt(REMOTE_ADDR, 1234, client='dummy')


def test_phishtank_urls():
    rule.remote = 'test/phishtank/feed.json.gz'
    x = s.process(rule, feed="urls")

    assert len(x) > 0
    assert len(x[0].indicator) > 4

    indicators = set()
    for i in x:
        indicators.add(i.indicator)

    assert 'http://charlesleonardconstruction.com/irs/confim/index.html' in indicators
