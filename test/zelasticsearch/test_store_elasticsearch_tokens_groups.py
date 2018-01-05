import pytest
from csirtg_indicator import Indicator
from cif.store import Store
from elasticsearch_dsl.connections import connections
import os
import arrow
from cifsdk.exceptions import AuthError
from pprint import pprint
import json

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
        group='everyone',
        lasttime=arrow.utcnow().datetime,
        reporttime=arrow.utcnow().datetime
    )


@pytest.mark.skipif(DISABLE_TESTS, reason='need to set CIF_ELASTICSEARCH_TEST=1 to run')
def test_store_elasticsearch_tokens_groups1(store, token, indicator):
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
    t = t['token']

    i = None
    try:
        i = store.handle_indicators_create(t, {
            'indicator': 'example.com',
            'group': 'staff2',
            'provider': 'example.com',
            'tags': ['test'],
            'itype': 'fqdn',
            'lasttime': arrow.utcnow().datetime,
            'reporttime': arrow.utcnow().datetime

        }, flush=True)
    except AuthError as e:
        pass

    assert i is None

    i = store.handle_indicators_create(t, {
        'indicator': 'example.com',
        'group': 'staff',
        'provider': 'example.com',
        'tags': ['test'],
        'itype': 'fqdn',
        'lasttime': arrow.utcnow().datetime,
        'reporttime': arrow.utcnow().datetime
    }, flush=True)

    assert i

    i = store.handle_indicators_search(t, {'itype': 'fqdn'})
    i = json.loads(i)
    i = [i['_source'] for i in i['hits']['hits']]
    assert len(list(i)) > 0

    pprint(i)

    i = store.handle_indicators_search(t, {'indicator': 'example.com'})
    assert len(list(i)) > 0


@pytest.mark.skipif(DISABLE_TESTS, reason='need to set CIF_ELASTICSEARCH_TEST=1 to run')
def test_store_elasticsearch_tokens_groups2(store, indicator):
    t = store.store.tokens.create({
        'username': 'test',
        'groups': ['staff'],
        'read': True,
        'write': True
    })

    i = None
    try:
        i = store.handle_indicators_create(t['token'], {
            'indicator': 'example.com',
            'group': 'staff2',
            'provider': 'example.com',
            'tags': ['test'],
            'itype': 'fqdn',
            'lasttime': arrow.utcnow().datetime,
            'reporttime': arrow.utcnow().datetime

        }, flush=True)
    except AuthError as e:
        pass

    assert i is None


@pytest.mark.skipif(DISABLE_TESTS, reason='need to set CIF_ELASTICSEARCH_TEST=1 to run')
def test_store_elasticsearch_tokens_groups3(store, indicator):
    t = store.store.tokens.create({
        'username': 'test',
        'groups': ['staff'],
        'write': True
    })

    t2 = store.store.tokens.create({
        'username': 'test',
        'groups': ['staff2'],
        'read': True,
    })

    i = store.handle_indicators_create(t['token'], {
        'indicator': 'example.com',
        'group': 'staff',
        'provider': 'example.com',
        'tags': ['test'],
        'itype': 'fqdn',
        'lasttime': arrow.utcnow().datetime,
        'reporttime': arrow.utcnow().datetime

    }, flush=True)

    assert i

    i = store.handle_indicators_search(t2['token'], {'itype': 'fqdn'})
    i = json.loads(i)
    assert len(i) == 0

    i = store.handle_indicators_search(t2['token'], {'indicator': 'example.com'})
    i = json.loads(i)
    assert len(i) == 0


@pytest.mark.skipif(DISABLE_TESTS, reason='need to set CIF_ELASTICSEARCH_TEST=1 to run')
def test_store_elasticsearch_tokens_groups4(store, indicator):
    t = store.store.tokens.create({
        'username': 'test',
        'groups': ['staff', 'staff2'],
        'write': True,
        'read': True
    })

    i = store.handle_indicators_create(t['token'], {
        'indicator': 'example.com',
        'group': 'staff',
        'provider': 'example.com',
        'tags': ['test'],
        'itype': 'fqdn',
        'lasttime': arrow.utcnow().datetime,
        'reporttime': arrow.utcnow().datetime

    }, flush=True)

    assert i

    i = store.handle_indicators_create(t['token'], {
        'indicator': 'example.com',
        'group': 'staff2',
        'provider': 'example.com',
        'tags': ['test'],
        'itype': 'fqdn',
        'lasttime': arrow.utcnow().datetime,
        'reporttime': arrow.utcnow().datetime

    }, flush=True)

    assert i

    i = store.handle_indicators_search(t['token'], {'itype': 'fqdn', 'groups': 'staff'})
    i = json.loads(i)
    i = [i['_source'] for i in i['hits']['hits']]
    assert len(i) == 1
