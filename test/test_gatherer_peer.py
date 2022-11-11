import pytest
from cif.gatherer.peers import Peer
from csirtg_indicator import Indicator
import warnings
from pprint import pprint
import os

DISABLE_TESTS = True
if os.environ.get('CIF_GATHERER_PEERS_TEST'):
    if os.environ['CIF_GATHERER_PEERS_TEST'] == '1':
        DISABLE_TESTS = False

os.environ['CIF_GATHERERS_PEERS_ENABLED'] = '1'

data = [
    '23028 | 216.90.108.0/24 | US | arin | 1998-09-25',
    '701 1239 3549 3561 7132 | 216.90.108.0/24 | US | arin | 1998-09-25',
]

@pytest.mark.skipif(DISABLE_TESTS, reason='need to set CIF_GATHERER_PEERS_TEST=1 to run')
def test_gatherer_peer():
    a = Peer()

    def _resolve(i):
        return data

    a._resolve_ns = _resolve
    x = a.process(Indicator(indicator='216.90.108.0'))

    if x.peers:
        assert 65535 > int(x.peers[0]['asn']) > 1
    else:
        warnings.warn('TC Not Responding...', UserWarning)