import py.test
import os

DISABLE_TESTS = True
if os.environ.get('CIF_RDFLIB_TEST') == '1':
    DISABLE_TESTS = False

from cif.store import Store
from csirtg_indicator import Indicator


@py.test.yield_fixture
def store():
    with Store(store_type='rdflib') as s:
        s._load_plugin()
        yield s


@py.test.mark.skipif(DISABLE_TESTS, reason='rdflib tests disabled')
def test_store_rdflib(store):
    store.token_create_admin()
    t = store.store.tokens_admin_exists()
    assert t

    i = [
        {
            'indicator': 'example.com',
            'itype': 'fqdn',
            'tags': 'malware',
            'provider': 'csirtgadgets.org',
        },
        {
            'indicator': 'example2.com',
            'itype': 'fqdn',
            'tags': 'malware',
            'provider': 'csirtgadgets.org',
        }
    ]

    x = store.handle_indicators_create(t, i)
    assert x > 0

    x = store.handle_indicators_search(t, {
        'indicator': 'example.com'
    })

    assert len(x) > 0
