import py.test

from cif.store import Store
from csirtg_indicator import Indicator

DISABLE_TESTS = False

try:
    import elasticsearch
except ImportError as e:
    DISABLE_TESTS = True

@py.test.yield_fixture
def store():
    with Store(store_type='elasticsearch') as s:
        yield s


# @py.test.mark.skipif(DISABLE_TESTS, reason='missing elasticsearch')
# def test_store_elasticsearch(store):
#     store.token_create_admin()
#     t = store.store.tokens_admin_exists()
#     assert t
#
#     i = [
#         Indicator(indicator='example.com', tags='botnet', provider='csirtgadgets.org').__dict__,
#         Indicator(indicator='example2.com', tags='malware', provider='csirtgadgets.org').__dict__
#     ]
#
#     x = store.handle_indicators_create(t, {
#         'indicator': 'example.com'
#     })
#     assert x > 0
#
#     x = store.handle_indicators_search(t, {
#         'indicator': 'example.com'
#     })
#
#     assert x > 0
