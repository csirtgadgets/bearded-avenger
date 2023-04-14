import pytest
from csirtg_indicator import Indicator
from cif.store import Store
from cif.auth import Auth
from elasticsearch_dsl.connections import connections
import os
import arrow
from cifsdk.exceptions import AuthError
from pprint import pprint
import ujson as json

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

    with Store(store_type='elasticsearch', nodes='127.0.0.1:9200', hunter_token='abc123') as s:
        s._load_plugin(nodes='127.0.0.1:9200')
        yield s

    try:
        assert connections.get_connection().indices.delete(index='indicators-*')
        assert connections.get_connection().indices.delete(index='tokens')
    except Exception:
        pass

@pytest.fixture
def auth():
    with Auth(store_type='elasticsearch', nodes='127.0.0.1:9200') as a:
        a._load_plugin(nodes='127.0.0.1:9200')
        yield a

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
def test_store_elasticsearch_tokens_groups1(store, auth, token, indicator):
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
    _t = auth.auth.handle_token_search(t['token'])

    mtype = 'indicators_create'
    data = json.dumps({
            'indicator': 'example.com',
            'group': 'staff2',
            'provider': 'example.com',
            'tags': ['test'],
            'itype': 'fqdn',
            'lasttime': arrow.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
            'reporttime': arrow.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ')

        })

    with pytest.raises(AuthError):
        auth.check_token_perms(mtype, _t, data)

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
def test_store_elasticsearch_tokens_groups2(store, auth, indicator):
    t = store.store.tokens.create({
        'username': 'test',
        'groups': ['staff'],
        'read': True,
        'write': True
    })

    _t = auth.auth.handle_token_search(t['token'])

    mtype = 'indicators_create'
    data = json.dumps({
            'indicator': 'example.com',
            'group': 'staff2',
            'provider': 'example.com',
            'tags': ['test'],
            'itype': 'fqdn',
            'lasttime': arrow.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
            'reporttime': arrow.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ')

        })

    with pytest.raises(AuthError):
        auth.check_token_perms(mtype, _t, data)


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

    i = store.handle_indicators_search(t2, {'itype': 'fqdn'})
    i = json.loads(i)
    assert len(i) == 0

    i = store.handle_indicators_search(t2, {'indicator': 'example.com'})
    i = json.loads(i)
    assert len(i) == 0

    i = store.handle_indicators_search(t2, {'indicator': 'example.com', 'groups': 'staff'})
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

    i = store.handle_indicators_create(t, {
        'indicator': 'example.com',
        'group': 'staff2',
        'provider': 'example.com',
        'tags': ['test'],
        'itype': 'fqdn',
        'lasttime': arrow.utcnow().datetime,
        'reporttime': arrow.utcnow().datetime

    }, flush=True)

    assert i

    i = store.handle_indicators_search(t, {'itype': 'fqdn', 'groups': 'staff'})
    i = json.loads(i)
    i = [i['_source'] for i in i['hits']['hits']]
    assert len(i) == 1

# test hunter submit to any group
@pytest.mark.skipif(DISABLE_TESTS, reason='need to set CIF_ELASTICSEARCH_TEST=1 to run')
def test_store_elasticsearch_tokens_groups5(store, token, indicator):
    t = store.store.tokens.create({
        'username': 'hunter',
        'groups': ['hunter_test'],
        'token': 'abc123',
        'write': True,
        'read': False
    })

    i = store.handle_indicators_create(t, {
        'indicator': 'example.com',
        'group': 'everyone',
        'provider': 'example.com',
        'tags': ['test'],
        'itype': 'fqdn',
        'lasttime': arrow.utcnow().datetime,
        'reporttime': arrow.utcnow().datetime

    }, flush=True)

    assert i

    i = store.handle_indicators_search(token, {'itype': 'fqdn', 'groups': 'everyone'})
    i = json.loads(i)
    i = [i['_source'] for i in i['hits']['hits']]
    assert len(i) == 1

# allow admin to access any group
@pytest.mark.skipif(DISABLE_TESTS, reason='need to set CIF_ELASTICSEARCH_TEST=1 to run')
def test_store_elasticsearch_tokens_groups6(store, token, indicator):
    t = store.store.tokens.create({
        'username': 'test',
        'groups': ['private'],
        'write': True,
        'read': False
    })

    i = store.handle_indicators_create(t, {
        'indicator': 'example.com',
        'group': 'private',
        'provider': 'example.com',
        'tags': ['test'],
        'itype': 'fqdn',
        'lasttime': arrow.utcnow().datetime,
        'reporttime': arrow.utcnow().datetime

    }, flush=True)

    assert i

    i = store.handle_indicators_search(token, {'itype': 'fqdn'})
    i = json.loads(i)
    i = [i['_source'] for i in i['hits']['hits']]
    assert i[0]['indicator'] == 'example.com'