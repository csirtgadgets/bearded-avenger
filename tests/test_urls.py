import pytest

from cif.observable import Observable


def _not(data):
    for d in data:
        d = Observable(d)
        assert d.otype != 'url'


def test_urls_ip():
    data = ['192.168.1.0/24', '192.168.1.1', '2001:1608:10:147::21', '2001:4860:4860::8888']
    _not(data)


def test_urls_fqdn():
    data = ['example.org', '1.2.3.4.com', 'xn----jtbbmekqknepg3a.xn--p1ai']
    _not(data)


def test_urls_ok():
    data = [
        'http://192.168.1.1/1.html',
        'http://www41.xzmnt.com',
        'http://get.ahoybest.com/n/3.6.16/12205897/microsoft lync server 2010.exe'
    ]

    for d in data:
        d = Observable(d)
        assert d.otype is 'url'
