import pytest

from csirtg_indicator import Indicator
from cif.store import Store
from elasticsearch_dsl.connections import connections
import os
from datetime import datetime
from uuid import uuid4
from cifsdk.exceptions import AuthError

DISABLE_TESTS = True
if os.environ.get('CIF_ELASTICSEARCH_TEST'):
    if os.environ['CIF_ELASTICSEARCH_TEST'] == '1':
        DISABLE_TESTS = False

@pytest.yield_fixture
def store():

    with Store(store_type='elasticsearch', nodes='127.0.0.1:9200') as s:
        s._load_plugin(nodes='127.0.0.1:9200')
        try:
            connections.get_connection().indices.delete(index='indicators-*')
            connections.get_connection().indices.delete(index='tokens')
        except Exception as e:
            pass
        yield s

    assert connections.get_connection().indices.delete(index='indicators-*')
    assert connections.get_connection().indices.delete(index='tokens')

@pytest.yield_fixture
def token(store):
    t = store.store.tokens.create({
        'username': u'test_admin',
        'groups': [u'everyone'],
        'read': u'1',
        'write': u'1',
        'admin': u'1'
    })

    assert t
    yield t['token']

@pytest.fixture
def indicator():
    return Indicator(
        indicator='example.com',
        tags='botnet',
        provider='csirtg.io',
        group='everyone'
    )

@pytest.fixture
def indicator_ipv6():
    return Indicator(
        indicator='2001:4860:4860::8888',
        tags='botnet',
        provider='csirtg.io',
        group='everyone'
    )


@pytest.mark.skipif(DISABLE_TESTS, reason='need to set CIF_ELASTICSEARCH_TEST=1 to run')
def test_store_elasticsearch_indicator(store, token, indicator):
    x = store.handle_indicators_create(token, indicator.__dict__())
    assert x > 0

    x = store.handle_indicators_search(token, {
        'indicator': 'example.com'
    })

    assert len(x) > 0


@pytest.mark.skipif(DISABLE_TESTS, reason='need to set CIF_ELASTICSEARCH_TEST=1 to run')
def test_store_elasticsearch_tokens(store, token):
    assert store.store.tokens.update_last_activity_at(token, datetime.now())
    assert store.store.tokens.check(token, 'read')
    assert store.store.tokens.read(token)
    assert store.store.tokens.write(token)
    assert store.store.tokens.admin(token)
    assert store.store.tokens.last_activity_at(token) is not None
    assert store.store.tokens._cache_check(token)
    assert store.store.tokens.update_last_activity_at(token, datetime.now())


@pytest.mark.skipif(DISABLE_TESTS, reason='need to set CIF_ELASTICSEARCH_TEST=1 to run')
def test_store_elasticsearch_tokens_advanced(store, token):
    x = store.handle_tokens_search(token, {'token': token})
    assert len(list(x)) > 0

    x = store.handle_tokens_search(token, {'admin': True})
    assert len(list(x)) > 0

    x = store.handle_tokens_search(token, {'write': True})
    assert len(list(x)) > 0

    t = store.store.tokens.create({
        'username': u'test_admin2',
        'groups': [u'everyone']
    })

    x = store.handle_tokens_search(token, {'admin': True})
    assert len(list(x)) == 1

    x = store.handle_tokens_search(token, {})
    assert len(list(x)) == 2

    # test last_activity_at
    x = store.handle_indicators_search(token, {
        'indicator': 'example.com'
    })

    x = store.store.tokens.update_last_activity_at(token, datetime.now())
    assert x

    assert store.store.tokens.last_activity_at(token)


@pytest.mark.skipif(DISABLE_TESTS, reason='need to set CIF_ELASTICSEARCH_TEST=1 to run')
def test_store_elasticsearch_tokens_groups(store, token, indicator):
    t = store.store.tokens.create({
        'username': 'test',
        'groups': ['staff', 'everyone'],
        'read': True,
        'write': True
    })

    assert t
    assert t['groups'] == ['staff', 'everyone']

    assert t['write']
    assert t['read']
    assert not t.get('admin')

    i = None
    try:
        i = store.store.indicators.create(t, {
            'indicator': 'example.com',
            'group': 'staff2',
            'provider': 'example.com',
            'tags': ['test'],
            'itype': 'fqdn'
        })
    except AuthError as e:
        pass

    assert i is None




@pytest.mark.skipif(DISABLE_TESTS, reason='need to set CIF_ELASTICSEARCH_TEST=1 to run')
def test_store_elasticsearch_ipv6(store, token, indicator_ipv6):
    x = store.handle_indicators_create(token, indicator_ipv6.__dict__())
    assert x > 0

    x = store.handle_indicators_search(token, {
        'indicator': '2001:4860:4860::8888'
    })

    assert len(x) > 0

    x = store.handle_indicators_search(token, {
        'indicator': '2001:4860::/32'
    })

    assert len(x) > 0
