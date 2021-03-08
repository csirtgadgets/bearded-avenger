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

@pytest.fixture
def indicator_ipv4():
    return Indicator(
        indicator='1.2.3.4',
        tags='botnet',
        provider='csirtg.io',
        group='everyone',
        lasttime=arrow.utcnow().datetime,
        reporttime=arrow.utcnow().datetime
    )

@pytest.mark.skipif(DISABLE_TESTS, reason='need to set CIF_ELASTICSEARCH_TEST=1 to run')
def test_store_elasticsearch_tokens_acls1(store, token, indicator):

    x = store.handle_indicators_create(token, indicator.__dict__(), flush=True)
    assert x > 0

    t = store.store.tokens.create({
        'username': 'test',
        'groups': ['everyone'],
        'acl': ['fqdn'],
        'read': True,
        'write': True
    })

    assert t
    assert t['acl'] == ['fqdn']

    t = t['token']

    i = None
    try:
        i = store.handle_indicators_search(t, {
            'indicator': 'example.com',
        })
    except AuthError as e:
        pass

    x = json.loads(i)
    x = [i['_source'] for i in x['hits']['hits']]

    pprint(x)

    assert x[0]['indicator'] == indicator.indicator

@pytest.mark.skipif(DISABLE_TESTS, reason='need to set CIF_ELASTICSEARCH_TEST=1 to run')
def test_store_elasticsearch_tokens_acls2(store, token, indicator):

    x = store.handle_indicators_create(token, indicator.__dict__(), flush=True)
    assert x > 0

    t = store.store.tokens.create({
        'username': 'test',
        'groups': ['everyone'],
        'acl': ['ipv4'],
        'read': True,
        'write': True
    })

    assert t
    assert t['acl'] == ['ipv4']

    t = t['token']

    i = None
    try:
        i = store.handle_indicators_search(t, {
            'indicator': 'example.com',
        })
    except AuthError as e:
        pass

    assert i == '{}'

@pytest.mark.skipif(DISABLE_TESTS, reason='need to set CIF_ELASTICSEARCH_TEST=1 to run')
def test_store_elasticsearch_tokens_acls3(store, token, indicator, indicator_ipv4):

    x = store.handle_indicators_create(token, indicator.__dict__(), flush=True)
    assert x > 0

    x = store.handle_indicators_create(token, indicator_ipv4.__dict__(), flush=True)
    assert x > 0

    t = store.store.tokens.create({
        'username': 'test',
        'groups': ['everyone'],
        'acl': ['fqdn','ipv4'],
        'read': True,
        'write': True
    })

    assert t
    assert t['acl'] == ['fqdn', 'ipv4']

    t = t['token']

    i = None

    try:
        i = store.handle_indicators_search(t, {
            'tags': 'botnet',
        })
    except AuthError as e:
        raise(AuthError)

    x = json.loads(i)
    x = [i['_source'] for i in x['hits']['hits']]

    pprint(x)

    assert x[0]['indicator'] in [indicator.indicator, indicator_ipv4.indicator]
    assert x[1]['indicator'] in [indicator.indicator, indicator_ipv4.indicator]

@pytest.mark.skipif(DISABLE_TESTS, reason='need to set CIF_ELASTICSEARCH_TEST=1 to run')
def test_store_elasticsearch_tokens_acls4(store, token, indicator):

    x = store.handle_indicators_create(token, indicator.__dict__(), flush=True)
    assert x > 0

    t = store.store.tokens.create({
        'username': 'test',
        'groups': ['everyone'],
        'acl': ['fqdn'],
        'read': True,
        'write': True
    })

    assert t
    assert t['acl'] == ['fqdn']

    t = t['token']

    i = None

    try:
        i = store.handle_indicators_search(t, {
            'indicator': 'example.com',
            'itype': 'fqdn'
        })
    except AuthError as e:
        raise(AuthError)

    x = json.loads(i)
    x = [i['_source'] for i in x['hits']['hits']]

    pprint(x)

    assert x[0]['indicator'] == indicator.indicator

@pytest.mark.skipif(DISABLE_TESTS, reason='need to set CIF_ELASTICSEARCH_TEST=1 to run')
def test_store_elasticsearch_tokens_acls5(store, indicator):

    t = store.store.tokens.create({
        'username': 'test',
        'groups': ['everyone'],
        'acl': ['ipv4'],
        'read': True,
        'write': True
    })

    assert t
    assert t['acl'] == ['ipv4']

    t = t['token']

    i = None
    with pytest.raises(AuthError):
        try:
            i = store.handle_indicators_search(t, {
                'indicator': 'example.com',
                'itype': 'fqdn'
            })
        except AuthError as e:
            raise(AuthError)

@pytest.mark.skipif(DISABLE_TESTS, reason='need to set CIF_ELASTICSEARCH_TEST=1 to run')
def test_store_elasticsearch_tokens_acls6(store, token, indicator):

    x = store.handle_indicators_create(token, indicator.__dict__(), flush=True)
    assert x > 0

    t = store.store.tokens.create({
        'username': 'test',
        'groups': ['everyone'],
        'acl': [''],
        'read': True,
        'write': True
    })

    assert t
    assert t['acl'] == ['']

    t = t['token']

    i = None

    try:
        i = store.handle_indicators_search(t, {
            'indicator': 'example.com',
        })
    except AuthError as e:
        raise(AuthError)

    x = json.loads(i)
    x = [i['_source'] for i in x['hits']['hits']]

    pprint(x)

    assert x[0]['indicator'] == indicator.indicator


@pytest.mark.skipif(DISABLE_TESTS, reason='need to set CIF_ELASTICSEARCH_TEST=1 to run')
def test_store_elasticsearch_tokens_acls7(store, token, indicator):

    x = store.handle_indicators_create(token, indicator.__dict__(), flush=True)
    assert x > 0

    t = store.store.tokens.create({
        'username': 'test',
        'groups': ['everyone'],
        'read': True,
        'write': True
    })

    assert t
    assert t.get('acl') == None

    t = t['token']

    i = None

    try:
        i = store.handle_indicators_search(t, {
            'indicator': 'example.com',
        })
    except AuthError as e:
        raise(AuthError)

    x = json.loads(i)
    x = [i['_source'] for i in x['hits']['hits']]

    pprint(x)

    assert x[0]['indicator'] == indicator.indicator