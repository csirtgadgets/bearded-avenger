import py.test

from cif.observable import Observable

##TODO bring over the new tests from v2


def test_obs_ipv4():
    o = Observable('192.168.1.1')
    assert o.is_private()
    assert o.observable == '192.168.1.1'
    assert o.otype == 'ipv4'


def test_obs_fqdn():
    o = Observable('example.org')

    assert o.is_private() is False
    assert o.observable == 'example.org'
    assert o.otype == 'fqdn'


def test_obs_url():
    o = Observable('http://example.org')

    assert o.is_private() is False
    assert o.observable == 'http://example.org'
    assert o.otype is not 'fqdn'
    assert o.otype is 'url'
