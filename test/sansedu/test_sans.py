import py.test

from csirtg_smrt import Smrt
from csirtg_smrt.rule import Rule
from cifsdk.constants import REMOTE_ADDR

rule = 'rules/default/sans_edu.yml'
rule = Rule(path=rule)
rule.fetcher = 'file'
s = Smrt(REMOTE_ADDR, 1234, client='dummy')


def test_sans_low():
    feed = '02_domains_low'
    rule.feeds[feed]['remote'] = 'test/sansedu/low.txt'
    x = s.process(rule, feed=feed)
    assert len(x) > 0

    assert len(x[0].indicator) > 4


def test_sans_block():
    feed = 'block'
    rule.feeds[feed]['remote'] = 'test/sansedu/block.txt'
    x = s.process(rule, feed=feed)

    assert len(x) > 0
    assert len(x[0].indicator) > 4
