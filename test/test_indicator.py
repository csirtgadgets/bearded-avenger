import py.test

from cif.indicator import Indicator

##TODO bring over the new tests from v2


def test_obs_ipv4():
    o = Indicator('192.168.1.1')
    assert o.is_private()
    assert o.indicator == '192.168.1.1'
    assert o.itype == 'ipv4'


def test_obs_fqdn():
    o = Indicator('example.org')

    assert o.is_private() is False
    assert o.indicator == 'example.org'
    assert o.itype == 'fqdn'


def test_obs_url():
    o = Indicator('http://example.org')

    assert o.is_private() is False
    assert o.indicator == 'http://example.org'
    assert o.itype is not 'fqdn'
    assert o.itype is 'url'
