from csirtg_indicator import Indicator

##TODO bring over the new tests from v2


def test_indicator_ipv4():
    i = Indicator('192.168.1.1')
    assert i.is_private()
    assert i.indicator == '192.168.1.1'
    assert i.itype == 'ipv4'


def test_indicator_fqdn():
    i = Indicator('example.org')

    assert i.is_private() is False
    assert i.indicator == 'example.org'
    assert i.itype == 'fqdn'


def test_indicator_url():
    i = Indicator('http://example.org')

    assert i.is_private() is False
    assert i.indicator == 'http://example.org'
    assert i.itype is not 'fqdn'
    assert i.itype is 'url'
