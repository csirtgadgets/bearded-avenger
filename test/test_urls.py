import pytest

from cif.indicator import Indicator


def _not(data):
    for d in data:
        d = Indicator(d)
        assert d.itype != 'url'


def test_urls_ip():
    data = ['192.168.1.0/24', '192.168.1.1', '2001:1608:10:147::21', '2001:4860:4860::8888']
    _not(data)


def test_urls_fqdn():
    data = ['example.org', '1.2.3.4.com', 'xn----jtbbmekqknepg3a.xn--p1ai']
    _not(data)


def test_urls_not_ok():
    data = [
        'http://wp-content/plugins/tinymce-advanced/mce/emoticons/img/Yahoo-login/yahoo.html'
    ]

    for d in data:
        try:
            d = Indicator(d)
            from pprint import pprint
            pprint(d)
        except NotImplementedError:
            pass
        else:
            raise NotImplementedError


def test_urls_ok():
    data = [
        'http://192.168.1.1/1.html',
        'http://www41.xzmnt.com',
        'http://get.ahoybest.com/n/3.6.16/12205897/microsoft lync server 2010.exe'
    ]

    for d in data:
        d = Indicator(d)
        assert d.itype is 'url'
