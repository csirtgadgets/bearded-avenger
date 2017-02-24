import py.test
from cif.gatherer.peers import Peer
from csirtg_indicator import Indicator
import warnings
from pprint import pprint

data = [
    '23028 | 216.90.108.0/24 | US | arin | 1998-09-25',
    '701 1239 3549 3561 7132 | 216.90.108.0/24 | US | arin | 1998-09-25',
]


def test_gatherer_peer():
    a = Peer()

    def _resolve(i):
        return data

    a._resolve_ns = _resolve
    x = a.process(Indicator(indicator='216.90.108.0'))

    if x.peers:
        assert x.peers[0]['asn'] == '23352'
    else:
        warnings.warn('TC Not Responding...', UserWarning)