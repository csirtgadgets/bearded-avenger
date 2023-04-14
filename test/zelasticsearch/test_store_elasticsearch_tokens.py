import pytest
from csirtg_indicator import Indicator
from cif.store import Store
from elasticsearch_dsl.connections import connections
import os
import arrow

DISABLE_TESTS = True
if os.environ.get('CIF_ELASTICSEARCH_TEST'):
    if os.environ['CIF_ELASTICSEARCH_TEST'] == '1':
        DISABLE_TESTS = False


@pytest.fixture
def store():
    try:
        connections.get_connection().indices.delete(index='indicators-*')
        connections.get_connection().indices.delete(index='tokens')
    except Exception as e:
        pass

    with Store(store_type='elasticsearch', nodes='127.0.0.1:9200') as s:
        s._load_plugin(nodes='127.0.0.1:9200')
        yield s

    try:
        assert connections.get_connection().indices.delete(index='indicators-*')
        assert connections.get_connection().indices.delete(index='tokens')
    except Exception:
        pass


@pytest.fixture
def token(store):
    t = store.store.tokens.create({
        'username': u'test_admin',
        'groups': [u'everyone'],
        'read': u'1',
        'write': u'1',
        'admin': u'1'
    })

    assert t
    yield t

@pytest.fixture
def indicator():
    return Indicator(
        indicator='example.com',
        tags='botnet',
        provider='csirtg.io',
        group='everyone',
        lasttime=arrow.utcnow().datetime,
        reporttime=arrow.utcnow().datetime
    )


@pytest.mark.skipif(DISABLE_TESTS, reason='need to set CIF_ELASTICSEARCH_TEST=1 to run')
def test_store_elasticsearch_tokens(store, token):
    # the below funcs should cache the checked token
    assert store.store.tokens.check(token, 'read')
    assert store.store.tokens.read(token)
    assert store.store.tokens.write(token)
    assert store.store.tokens.admin(token)
    assert store.store.tokens._cache_check(token['token']) is not False


@pytest.mark.skipif(DISABLE_TESTS, reason='need to set CIF_ELASTICSEARCH_TEST=1 to run')
def test_store_elasticsearch_tokens_advanced(store, token):
    x = store.handle_tokens_search(token, {'token': token['token']})
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
    now_str = arrow.utcnow().datetime.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
    # the below func should update last_activity_at and cache that
    assert store.store.tokens.auth_search({'token': t['token']})

    assert store.store.tokens.last_activity_at(t) > now_str
