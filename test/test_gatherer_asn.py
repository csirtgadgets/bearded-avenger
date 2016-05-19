import py.test
from cif.gatherer.asn import Asn
from csirtg_indicator import Indicator
from pprint import pprint

data = [
    '23028 | 216.90.108.0/24 | US | arin | 1998-09-25',
    '701 1239 3549 3561 7132 | 216.90.108.0/24 | US | arin | 1998-09-25',
]


def test_gatherer_asn():
    a = Asn()

    def _resolve(i):
        return data

    a._resolve_ns = _resolve
    x = a.process(Indicator(indicator='216.90.108.0'))

    assert x.asn == '23028'
    assert x.asn_desc.startswith('TEAM-CYMRU')


