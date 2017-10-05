import py.test
from cif.gatherer.geo import Geo
from csirtg_indicator import Indicator
from pprint import pprint

data = {
    'cc': 'US',
    'city': 'Chesterfield'
}


def test_gatherer_geo_v4():
    a = Geo()

    def _resolve(i):
        i.cc = data['cc']
        i.city = data['city']

    a._resolve = _resolve

    i = Indicator(indicator='216.90.108.0')

    a.process(i)

    assert i.cc == data['cc']
    assert i.city == data['city']


def test_gatherer_geo_v6():
    a = Geo()

    def _resolve(i):
        i.cc = data['cc']
        i.city = data['city']

    a._resolve = _resolve

    i = Indicator(indicator='2607:ff10::c0:1:1:10d')

    a.process(i)

    assert i.cc == data['cc']
    assert i.city == data['city']
