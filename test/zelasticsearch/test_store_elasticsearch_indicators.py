import pytest
from csirtg_indicator import Indicator
from cif.store import Store
from elasticsearch_dsl.connections import connections
import os
import arrow

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

    assert len(x) > 0
