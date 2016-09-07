import pytest

from cif.store import Store
from csirtg_indicator import Indicator

DISABLE_TESTS = False

try:
    import elasticsearch
except ImportError as e:
    DISABLE_TESTS = True

# @pytest.yield_fixture
# def store():
#     with Store(store_type='elasticsearch') as s:
#         yield s
#
# @pytest.fixture
# def indicator():
#     return {
#         'indicator': 'example.com',
#         'tags': ['botnet'],
#         'provider': 'csirtgadgets.org'
#     }
#
#
# @pytest.mark.skipif(DISABLE_TESTS, reason='missing elasticsearch')
# def test_store_elasticsearch(store, indicator):
#     store.token_create_admin()
#     # t = store.store.tokens_admin_exists()
#     # assert t
#     #
#     # x = store.handle_indicators_create(t, indicator)
#     # assert x > 0
#     #
#     # x = store.handle_indicators_search(t, indicator)
#     #
#     # assert x > 0
