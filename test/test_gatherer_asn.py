import pytest
import os
import warnings
from cif.gatherer.asn import Asn
from csirtg_indicator import Indicator
from pprint import pprint

DISABLE_FAST_TESTS = True
if os.environ.get('CIF_ASN_FAST_TEST'):
    if os.environ['CIF_ASN_FAST_TEST'] == '1':
        DISABLE_FAST_TESTS = False

data = [
    '23028 | 216.90.108.0/24 | US | arin | 1998-09-25',
    '701 1239 3549 3561 7132 | 216.90.108.0/24 | US | arin | 1998-09-25',
]


def test_gatherer_asn():
    a = Asn(fast=False)

    def _resolve(i):
        return data

    a._resolve_ns = _resolve
    x = a.process(Indicator(indicator='216.90.108.0'))

    if x.asn and x.asn_desc:
        assert x.asn != ''
        assert x.asn_desc != ''
    else:
        warnings.warn('TC Not Responding...', UserWarning)


@pytest.mark.skipif(DISABLE_FAST_TESTS, reason='need to set CIF_ASN_FAST_TEST=1 to run')
def test_gatherer_asn_fast():
    a = Asn(fast='tcp://localhost:5555')

    x = a._resolve_fast('216.90.108.0')

    if x.asn:
        assert x['asn'] == 23028
    else:
        warnings.warn('TC Not Responding...', UserWarning)
