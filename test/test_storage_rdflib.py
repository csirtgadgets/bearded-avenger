import py.test

from cif.storage import Storage
from csirtg_indicator import Indicator


@py.test.yield_fixture
def storage():
    with Storage(store='rdflib') as s:
        yield s


def test_storage_rdflib(storage):
    storage.token_create_admin()
    t = storage.store.tokens_admin_exists()
    assert t

    i = [
        Indicator(indicator='example.com', tags='botnet', provider='csirtgadgets.org').__dict__,
        Indicator(indicator='example2.com', tags='malware', provider='csirtgadgets.org').__dict__
    ]

    x = storage.handle_indicators_create(t, i)
    assert x > 0

    x = storage.handle_indicators_search(t, {
        'indicator': 'example.com'
    })

    assert x > 0
