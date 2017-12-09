import pytest
from csirtg_indicator import Indicator
from cif.store import Store
from elasticsearch_dsl.connections import connections
import os
import arrow
import json
from pprint import pprint

DISABLE_TESTS = True
if os.environ.get('CIF_ELASTICSEARCH_TEST'):
    if os.environ['CIF_ELASTICSEARCH_TEST'] == '1':
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
        reporttime=arrow.utcnow().datetime
    )


@pytest.fixture
def indicator_email():
    return Indicator(
        indicator='user.12.3@example.net',
        tags='botnet',
        provider='csirtg.io',
        group='everyone',
        lasttime=arrow.utcnow().datetime,
        reporttime=arrow.utcnow().datetime
    )


@pytest.fixture
def indicator_ipv6():
    return Indicator(
        indicator='2001:4860:4860::8888',
        tags='botnet',
        provider='csirtg.io',
        group='everyone',
        lasttime=arrow.utcnow().datetime,
        reporttime=arrow.utcnow().datetime
    )

@pytest.fixture
def indicator_url():
    return Indicator(
        indicator='http://pwmsteel.com/dhYtebv3',
        tags='exploit',
        provider='csirtg.io',
        group='everyone',
        lasttime=arrow.utcnow().datetime,
        reporttime=arrow.utcnow().datetime
    )

@pytest.fixture
def indicator_malware():
    return Indicator(
        indicator='d52380918a07322c50f1bfa2b43af3bb54cb33db',
        tags='malware',
        provider='csirtg.io',
        group='everyone',
        lasttime=arrow.utcnow().datetime,
        reporttime=arrow.utcnow().datetime
    )


@pytest.mark.skipif(DISABLE_TESTS, reason='need to set CIF_ELASTICSEARCH_TEST=1 to run')
def test_store_elasticsearch_indicators(store, token, indicator):
    x = store.handle_indicators_create(token, indicator.__dict__(), flush=True)
    assert x > 0

    x = store.handle_indicators_search(token, {
        'indicator': 'example.com'
    })

    assert len(x) > 0


@pytest.mark.skipif(DISABLE_TESTS, reason='need to set CIF_ELASTICSEARCH_TEST=1 to run')
def test_store_elasticsearch_indicators_ipv6(store, token, indicator_ipv6):
    x = store.handle_indicators_create(token, indicator_ipv6.__dict__(), flush=True)

    assert x > 0

    x = store.handle_indicators_search(token, {
        'indicator': '2001:4860:4860::8888'
    })

    assert len(x) > 0


    x = store.handle_indicators_search(token, {
        'indicator': '2001:4860::/32'
    })

    assert len(x) > 0


@pytest.mark.skipif(DISABLE_TESTS, reason='need to set CIF_ELASTICSEARCH_TEST=1 to run')
def test_store_elasticsearch_indicators_email(store, token, indicator_email):
    x = store.handle_indicators_create(token, indicator_email.__dict__(), flush=True)

    assert x > 0

    x = store.handle_indicators_search(token, {
        'indicator': indicator_email.indicator,
    })

    assert len(x) > 0

    x = store.handle_indicators_search(token, {
        'indicator': '*user*',
    })

    assert len(x) > 0

    x = store.handle_indicators_search(token, {
        'indicator': '%example%',
    })

    x = json.loads(x)
    x = [i['_source'] for i in x['hits']['hits']]

    assert len(x) > 0

    assert(x[0]['lasttime'])
    assert(x[0]['firsttime'])
    assert (x[0]['reporttime'])


@pytest.mark.skipif(DISABLE_TESTS, reason='need to set CIF_ELASTICSEARCH_TEST=1 to run')
def test_store_elasticsearch_indicators_url(store, token, indicator_url):
    x = store.handle_indicators_create(token, indicator_url.__dict__(), flush=True)

    assert x > 0

    x = store.handle_indicators_search(token, {
        'indicator': indicator_url.indicator,
    })

    assert len(x) > 0

    x = store.handle_indicators_search(token, {
        'indicator': '*pwmsteel.com*',
    })

    assert len(x) > 0

    x = store.handle_indicators_search(token, {
        'indicator': '%pwmsteel.com%',
    })

    x = json.loads(x)
    x = [i['_source'] for i in x['hits']['hits']]

    assert len(x) > 0

    assert(x[0]['lasttime'])
    assert(x[0]['firsttime'])
    assert (x[0]['reporttime'])


@pytest.mark.skipif(DISABLE_TESTS, reason='need to set CIF_ELASTICSEARCH_TEST=1 to run')
def test_store_elasticsearch_indicators_malware(store, token, indicator_malware):
    x = store.handle_indicators_create(token, indicator_malware.__dict__(), flush=True)

    assert x > 0

    x = store.handle_indicators_search(token, {
        'indicator': indicator_malware.indicator,
    })

    assert len(x) > 0

    x = store.handle_indicators_search(token, {
        'indicator': '*a07322c50*',
    })

    assert len(x) > 0

    x = store.handle_indicators_search(token, {
        'indicator': '%a07322c50%',
    })

    x = json.loads(x)
    x = [i['_source'] for i in x['hits']['hits']]

    assert len(x) > 0

    assert(x[0]['lasttime'])
    assert(x[0]['firsttime'])
    assert (x[0]['reporttime'])

    assert x[0]['indicator'] == indicator_malware.indicator
