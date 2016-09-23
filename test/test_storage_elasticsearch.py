import pytest

from cif.store import Store
from elasticsearch_dsl.connections import connections
import os

DISABLE_TESTS = True
if os.environ.get('CIF_ELASTICSEARCH_TEST'):
    if os.environ['CIF_ELASTICSEARCH_TEST'] == '1':
        DISABLE_TESTS = False

@pytest.yield_fixture
def store():

    with Store(store_type='elasticsearch', nodes='192.168.99.100:9200') as s:
        s._load_plugin(nodes='192.168.99.100:9200')
        try:
            connections.get_connection().indices.delete(index='indicators-*')
            connections.get_connection().indices.delete(index='tokens')
        except Exception as e:
            pass
        yield s

    #assert connections.get_connection().indices.delete(index='indicators-*')
    #assert connections.get_connection().indices.delete(index='tokens')

@pytest.yield_fixture
def token(store):
    t = store.store.tokens_create({
        'username': u'test_admin',
        'groups': [u'everyone'],
        'read': u'1',
        'write': u'1',
        'admin': u'1'
    })

    assert t
    t = t['token']
    yield t

@pytest.fixture
def indicator():
    return {
        'indicator': 'example.com',
        'tags': ['botnet'],
        'provider': 'csirtgadgets.org',
        'group': ['everyone']
    }

@pytest.fixture
def indicator_ipv6():
    return {
        'indicator': '2001:4860:4860::8888',
        'tags': ['botnet'],
        'provider': 'csirtgadgets.org',
        'group': ['everyone']
    }


@pytest.mark.skipif(DISABLE_TESTS, reason='need to set CIF_ELASTICSEARCH_TEST=1 to run')
def test_store_elasticsearch(store, token, indicator):
    x = store.handle_indicators_create(token, indicator)
    assert x > 0

    x = store.handle_indicators_search(token, {
        'indicator': 'example.com'
    })

    assert len(x) > 0


@pytest.mark.skipif(DISABLE_TESTS, reason='need to set CIF_ELASTICSEARCH_TEST=1 to run')
def test_store_elasticsearch_ipv6(store, token, indicator_ipv6):
    x = store.handle_indicators_create(token, indicator_ipv6)
    assert x > 0

    x = store.handle_indicators_search(token, {
        'indicator': '2001:4860:4860::8888'
    })

    assert len(x) > 0

    x = store.handle_indicators_search(token, {
        'indicator': '2001:4860::/32'
    })

    assert len(x) > 0

