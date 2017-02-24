import py.test
from cif.gatherer.peers import Peer
from csirtg_indicator import Indicator
from pprint import pprint
import warnings
import os

os.environ['CIF_GATHERERS_PEERS_ENABLED'] = '1'

data = [
    '701 1239 3549 3561 7132 | 216.90.108.0/24 | US | arin | 1998-09-25',
]


def test_gatherer_peers():
    p = Peer()

    def _resolve(i):
        return data

    p._resolve_ns = _resolve
    x = p.process(Indicator(indicator='216.90.108.0'))

    if x.peers:
        mypeers = set()
        for pp in x.peers:
            mypeers.add(pp['asn'])

        assert '2381' in mypeers
    else:
        warnings.warn('TC Not Responding...', UserWarning)

