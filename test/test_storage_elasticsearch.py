import py.test

from cif.store import Store
from csirtg_indicator import Indicator


@py.test.yield_fixture
def store():
    with Store(store='elasticsearch') as s:
        yield s


def test_store_elasticsearch(store):
    store.token_create_admin()
    t = store.store.tokens_admin_exists()
    assert t

    i = [
        Indicator(indicator='example.com', tags='botnet', provider='csirtgadgets.org').__dict__,
        Indicator(indicator='example2.com', tags='malware', provider='csirtgadgets.org').__dict__
    ]

    x = store.handle_indicators_create(t, {
        'indicator': 'example.com'
    })
    assert x > 0

    x = store.handle_indicators_search(t, {
        'indicator': 'example.com'
    })

    assert x > 0
