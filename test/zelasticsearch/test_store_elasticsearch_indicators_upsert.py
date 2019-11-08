import pytest
from csirtg_indicator import Indicator
from elasticsearch_dsl.connections import connections
from cif.store import Store
import os
import arrow
import json
from pprint import pprint
from imp import reload

DISABLE_TESTS = True
if os.environ.get('CIF_ELASTICSEARCH_TEST') and os.environ.get('CIF_STORE_ES_UPSERT_MODE'):
    if os.environ['CIF_ELASTICSEARCH_TEST'] == '1' and os.environ['CIF_STORE_ES_UPSERT_MODE'] == '1':
        DISABLE_TESTS = False

@pytest.yield_fixture
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
        reporttime=arrow.utcnow().datetime,
        confidence=7.0
    )

@pytest.fixture
def indicator2():
    return Indicator(
        indicator='example.org',
        tags='botnet',
        provider='csirtg.io',
        group='everyone',
        lasttime=arrow.utcnow().datetime,
        reporttime=arrow.utcnow().datetime,
        confidence=7.0
    )

@pytest.fixture
def indicator3():
    return Indicator(
        indicator='example.com',
        tags='botnet',
        provider='test-provider',
        group='everyone',
        lasttime=arrow.utcnow().datetime,
        reporttime=arrow.utcnow().datetime,
        confidence=7.0
    )

@pytest.fixture
def indicator4():
    return Indicator(
        indicator='example.com',
        tags='botnet',
        provider='test-provider',
        group='everyone',
        lasttime=arrow.utcnow().datetime,
        reporttime=arrow.utcnow().datetime,
        confidence=8.0
    )

@pytest.fixture
def new_indicator():
    return Indicator(
        indicator='example.com',
        tags='botnet',
        provider='csirtg.io',
        group='everyone',
        lasttime=arrow.utcnow().shift(days=+1),
        reporttime=arrow.utcnow().shift(days=+1)
    )

## test duplicate indicator submission, same lasttime
@pytest.mark.skipif(DISABLE_TESTS, reason='need to set CIF_ELASTICSEARCH_TEST=1 to run')
def test_store_elasticsearch_indicators_upsert1(store, token, indicator):

    x = store.handle_indicators_create(token, indicator.__dict__(), flush=True)
    assert x == 1

    x = store.handle_indicators_search(token, {
        'indicator': 'example.com',
        'nolog': 1
    })


    x = json.loads(x)
    x = [i['_source'] for i in x['hits']['hits']]

    assert len(x) == 1

    x = store.handle_indicators_create(token, indicator.__dict__(), flush=True)
    assert x == 0

    x = store.handle_indicators_search(token, {
        'indicator': 'example.com',
        'nolog': 1
    })

    x = json.loads(x)
    x = [i['_source'] for i in x['hits']['hits']]

    pprint(x)

    assert len(x) == 1
    assert x[0]['count'] == 1

## test duplicate indicator submission, different lasttime
@pytest.mark.skipif(DISABLE_TESTS, reason='need to set CIF_ELASTICSEARCH_TEST=1 to run')
def test_store_elasticsearch_indicators_upsert2(store, token, indicator, new_indicator):

    pprint(indicator)

    x = store.handle_indicators_create(token, indicator.__dict__(), flush=True)
    assert x == 1

    x = store.handle_indicators_search(token, {
        'indicator': 'example.com',
        'nolog': 1
    })


    x = json.loads(x)
    x = [i['_source'] for i in x['hits']['hits']]

    assert len(x) == 1
    assert x[0]['count'] == 1

    pprint(new_indicator)

    x = store.handle_indicators_create(token, new_indicator.__dict__(), flush=True)
    assert x == 1

    x = store.handle_indicators_search(token, {
        'indicator': 'example.com',
        'nolog': 1
    })

    x = json.loads(x)
    x = [i['_source'] for i in x['hits']['hits']]

    pprint(x)

    assert len(x) == 1
    assert x[0]['count'] == 2

## test different indicator submission, different indicator
@pytest.mark.skipif(DISABLE_TESTS, reason='need to set CIF_ELASTICSEARCH_TEST=1 to run')
def test_store_elasticsearch_indicators_upsert3(store, token, indicator, indicator2):

    pprint(indicator)

    x = store.handle_indicators_create(token, indicator.__dict__(), flush=True)
    assert x == 1

    pprint(indicator2)

    y = store.handle_indicators_create(token, indicator2.__dict__(), flush=True)
    assert y == 1

    x = store.handle_indicators_search(token, {
        'indicator': 'example.com',
        'nolog': 1
    })

    y = store.handle_indicators_search(token, {
        'indicator': 'example.org',
        'nolog': 1
    })

    x = json.loads(x)
    x = [i['_source'] for i in x['hits']['hits']]

    pprint(x)

    assert len(x) == 1
    assert x[0]['count'] == 1

    pprint(y)

    y = json.loads(y)
    y = [i['_source'] for i in y['hits']['hits']]

    assert len(y) == 1
    assert y[0]['count'] == 1

## test different indicator submission, different provider
@pytest.mark.skipif(DISABLE_TESTS, reason='need to set CIF_ELASTICSEARCH_TEST=1 to run')
def test_store_elasticsearch_indicators_upsert4(store, token, indicator, indicator3):

    pprint(indicator)

    x = store.handle_indicators_create(token, indicator.__dict__(), flush=True)
    assert x == 1

    pprint(indicator3)

    y = store.handle_indicators_create(token, indicator3.__dict__(), flush=True)
    assert y == 1

    x = store.handle_indicators_search(token, {
        'indicator': 'example.com',
        'provider': 'csirtg.io',
        'nolog': 1
    })

    y = store.handle_indicators_search(token, {
        'indicator': 'example.com',
        'provider': 'test-provider',
        'nolog': 1
    })

    x = json.loads(x)
    x = [i['_source'] for i in x['hits']['hits']]

    pprint(x)

    assert len(x) == 1
    assert x[0]['count'] == 1

    pprint(y)

    y = json.loads(y)
    y = [i['_source'] for i in y['hits']['hits']]

    assert len(y) == 1
    assert y[0]['count'] == 1

## test different indicator submission, different confidence
@pytest.mark.skipif(DISABLE_TESTS, reason='need to set CIF_ELASTICSEARCH_TEST=1 to run')
def test_store_elasticsearch_indicators_upsert5(store, token, indicator, indicator4):

    pprint(indicator)

    x = store.handle_indicators_create(token, indicator.__dict__(), flush=True)
    assert x == 1

    pprint(indicator4)

    y = store.handle_indicators_create(token, indicator4.__dict__(), flush=True)
    assert y == 1

    x = store.handle_indicators_search(token, {
        'indicator': 'example.com',
        'nolog': 1
    })

    x = json.loads(x)
    x = [i['_source'] for i in x['hits']['hits']]

    pprint(x)

    assert len(x) == 2
