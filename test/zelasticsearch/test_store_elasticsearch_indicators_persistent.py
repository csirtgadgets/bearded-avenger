import pytest
from csirtg_indicator import Indicator
from cif.store import Store
from elasticsearch_dsl.connections import connections
import os
import arrow
import ujson as json
from collections import Counter
from pprint import pprint

DISABLE_TESTS = True
if os.environ.get('CIF_ELASTICSEARCH_TEST', '0') == '1':
    DISABLE_TESTS = False

DISABLE_UPSERT_TESTS = True
if os.environ.get('CIF_STORE_ES_UPSERT_MODE', '0') == '1':
    DISABLE_UPSERT_TESTS = False

es_node = '127.0.0.1:9200'


@pytest.fixture(scope='module', autouse=True)
def store():
    try:
        connections.get_connection().indices.delete(index='indicators-*')
        connections.get_connection().indices.delete(index='tokens')
    except Exception as e:
        pass

    with Store(store_type='elasticsearch', nodes=es_node) as s:
        s._load_plugin(nodes=es_node)
        yield s

    try:
        assert connections.get_connection().indices.delete(index='indicators-*')
        assert connections.get_connection().indices.delete(index='tokens')
    except Exception:
        pass

@pytest.fixture(scope='module', autouse=True)
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
def indicator_ipv4_single_1():
    return Indicator(
        indicator='15.197.34.7',
        tags='cdn',
        confidence=8,
        provider='amazonaws.com',
        group='everyone',
        lasttime=arrow.utcnow().datetime,
        reporttime=arrow.utcnow().datetime
    )

@pytest.fixture
def indicator_ipv4_single_2():
    return Indicator(
        indicator='15.197.34.76',
        tags='cdn',
        confidence=8,
        provider='amazonaws.com',
        group='everyone',
        lasttime=arrow.utcnow().datetime,
        reporttime=arrow.utcnow().datetime
    )

@pytest.fixture
def indicator_ipv4_cidr_24():
    return Indicator(
        indicator='15.197.34.0/24',
        tags='cdn',
        confidence=7,
        provider='amazonaws.com',
        group='everyone',
        lasttime=arrow.utcnow().datetime,
        reporttime=arrow.utcnow().datetime
    )

@pytest.fixture
def indicator_ipv4_cidr_23():
    return Indicator(
        indicator='15.197.34.0/23',
        tags='cdn',
        confidence=7,
        provider='amazonaws.com',
        group='everyone',
        lasttime=arrow.utcnow().datetime,
        reporttime=arrow.utcnow().datetime
    )

@pytest.fixture
def indicator_ipv4_cidr_18():
    return Indicator(
        indicator='15.197.0.0/18',
        tags='cdn',
        confidence=7,
        provider='amazonaws.com',
        group='everyone',
        lasttime=arrow.utcnow().datetime,
        reporttime=arrow.utcnow().datetime
    )

@pytest.fixture
def indicator_ipv6_single_1():
    return Indicator(
        indicator='fd00:dead:beef:64:34:0::1',
        tags='cdn',
        confidence=9,
        provider='csirtg.io',
        group='everyone',
        lasttime=arrow.utcnow().datetime,
        reporttime=arrow.utcnow().datetime
    )

@pytest.fixture
def indicator_ipv6_single_2():
    return Indicator(
        indicator='fd00:dead:beef:64:35:0::1', # shouldn't be in the CIDR
        tags='cdn',
        confidence=7,
        provider='csirtg.io',
        group='everyone',
        lasttime=arrow.utcnow().datetime,
        reporttime=arrow.utcnow().datetime
    )

@pytest.fixture
def indicator_ipv6_cidr_80():
    return Indicator(
        indicator='fd00:dead:beef:64:34::/80',
        tags='cdn',
        confidence=7,
        provider='csirtg.io',
        group='everyone',
        lasttime=arrow.utcnow().datetime,
        reporttime=arrow.utcnow().datetime
    )

@pytest.fixture
def indicator_ssdeep_1():
    return Indicator(
        indicator='3:AXGBicFlgVNhBGcL6wCrFQEv:AXGHsNhxLsr2C',
        tags='test',
        confidence=6,
        provider='jessek',
        group='everyone',
        lasttime=arrow.utcnow().datetime,
        reporttime=arrow.utcnow().datetime
    )

# homology of ssdeep_1
@pytest.fixture
def indicator_ssdeep_2():
    return Indicator(
        indicator='3:AXGBicFlIHBGcL6wCrFQEv:AXGH6xLsr2C',
        tags='test',
        confidence=6,
        provider='jessek',
        group='everyone',
        lasttime=arrow.utcnow().datetime,
        reporttime=arrow.utcnow().datetime
    )

# totally different from ssdeep_1 and _2
@pytest.fixture
def indicator_ssdeep_3():
    return Indicator(
        indicator='3:hMCEOE8+DTfMSizNqcyEbYQJBFdoE7zXL:huOd+DQSizNqCb9Jzd5zb',
        tags='test',
        confidence=6,
        provider='jessek',
        group='everyone',
        lasttime=arrow.utcnow().datetime,
        reporttime=arrow.utcnow().datetime
    )

# store several indicators
@pytest.mark.skipif(DISABLE_TESTS, reason='need to set CIF_ELASTICSEARCH_TEST=1 to run')
def test_store_ipv4_cidr_24(store, token, indicator_ipv4_cidr_24):
    x = store.handle_indicators_create(token, indicator_ipv4_cidr_24.__dict__(), flush=True)
    assert x  == 1

@pytest.mark.skipif(DISABLE_TESTS, reason='need to set CIF_ELASTICSEARCH_TEST=1 to run')
def test_store_ipv4_single_1(store, token, indicator_ipv4_single_1):
    x = store.handle_indicators_create(token, indicator_ipv4_single_1.__dict__(), flush=True)
    assert x  == 1

@pytest.mark.skipif(DISABLE_TESTS, reason='need to set CIF_ELASTICSEARCH_TEST=1 to run')
def test_store_ipv4_single_2(store, token, indicator_ipv4_single_2):
    x = store.handle_indicators_create(token, indicator_ipv4_single_2.__dict__(), flush=True)
    assert x  == 1

@pytest.mark.skipif(DISABLE_TESTS, reason='need to set CIF_ELASTICSEARCH_TEST=1 to run')
def test_store_ipv4_cidr_23(store, token, indicator_ipv4_cidr_23):
    x = store.handle_indicators_create(token, indicator_ipv4_cidr_23.__dict__(), flush=True)
    assert x  == 1

@pytest.mark.skipif(DISABLE_TESTS, reason='need to set CIF_ELASTICSEARCH_TEST=1 to run')
def test_store_ipv4_cidr_18(store, token, indicator_ipv4_cidr_18):
    x = store.handle_indicators_create(token, indicator_ipv4_cidr_18.__dict__(), flush=True)
    assert x  == 1

@pytest.mark.skipif(DISABLE_TESTS, reason='need to set CIF_ELASTICSEARCH_TEST=1 to run')
def test_store_ssdeep_1(store, token, indicator_ssdeep_1):
    x = store.handle_indicators_create(token, indicator_ssdeep_1.__dict__(), flush=True)
    assert x  == 1

@pytest.mark.skipif(DISABLE_TESTS, reason='need to set CIF_ELASTICSEARCH_TEST=1 to run')
def test_store_ssdeep_2(store, token, indicator_ssdeep_2):
    x = store.handle_indicators_create(token, indicator_ssdeep_2.__dict__(), flush=True)
    assert x  == 1

@pytest.mark.skipif(DISABLE_TESTS, reason='need to set CIF_ELASTICSEARCH_TEST=1 to run')
def test_store_ssdeep_3(store, token, indicator_ssdeep_3):
    x = store.handle_indicators_create(token, indicator_ssdeep_3.__dict__(), flush=True)
    assert x  == 1

# now that we've stored a few indicators, let's try searching

# normal backend searches (allowlists for feed pulls, upsert searches) should NOT find IP relatives
@pytest.mark.skipif(DISABLE_TESTS, reason='need to set CIF_ELASTICSEARCH_TEST=1 to run')
def test_search_ipv4_single_1_backend(store, token, indicator_ipv4_single_1):
    search_filter = {
        'indicator': indicator_ipv4_single_1.__dict__()['indicator'],
        'nolog': 1
    }
    x = store.handle_indicators_search(token, search_filter)
    x = json.loads(x)
    y = [i['_source'] for i in x['hits']['hits']]
    assert isinstance(y, list)
    assert len(y) == 1
    # ensure none of the other indicator submissions after single_1 matched on upsert search
    assert y[0]['count'] == 1

# normal frontend searches (HTTP GET /indicators) SHOULD find IP relatives
@pytest.mark.skipif(DISABLE_TESTS, reason='need to set CIF_ELASTICSEARCH_TEST=1 to run')
def test_search_ipv4_single_1_frontend(store, token, indicator_ipv4_single_1):
    indicator = indicator_ipv4_single_1.__dict__()['indicator']
    search_filter = {
        'indicator': indicator,
        'nolog': 1,
        'find_relatives': True
    }
    x = store.handle_indicators_search(token, search_filter)
    x = json.loads(x)
    y = [i['_source'] for i in x['hits']['hits']]
    assert isinstance(y, list)
    # ensure there are 4 results: 1 identical match and 3 parent CIDRs
    assert len(y) == 4

    ilist = [i['indicator'] for i in y]
    icount_dict = Counter(ilist)
    assert icount_dict.get(indicator, 0) == 1

    cidr_count = sum(1 for i in ilist if '/' in i)
    assert cidr_count == 3

# normal frontend searches (HTTP GET /indicators) SHOULD find IP relatives
@pytest.mark.skipif(DISABLE_TESTS, reason='need to set CIF_ELASTICSEARCH_TEST=1 to run')
def test_search_ipv4_cidr_23_frontend(store, token, indicator_ipv4_cidr_23):
    indicator = indicator_ipv4_cidr_23.__dict__()['indicator']
    search_filter = {
        'indicator': indicator,
        'nolog': 1,
        'find_relatives': True
    }
    x = store.handle_indicators_search(token, search_filter)
    x = json.loads(x)
    y = [i['_source'] for i in x['hits']['hits']]
    assert isinstance(y, list)
    # ensure there are 5 results: 1 identical match, 2 relative CIDRs (1 parent, 1 child), and 2 child IPs
    assert len(y) == 5

    # every indicator should have a count of 1 (no single indicator was added twice)
    for i in y:
        assert i['count'] == 1

    ilist = [i['indicator'] for i in y]
    icount_dict = Counter(ilist)
    # every indicator should be unique
    for k in icount_dict.keys():
        assert icount_dict[k] == 1

    cidr_count = 0
    singleip_count = 0
    for i in ilist:
        if '/' in i:
            cidr_count += 1
        else:
            singleip_count += 1

    assert cidr_count == 3
    assert singleip_count == 2

# test search sort param working
@pytest.mark.skipif(DISABLE_TESTS, reason='need to set CIF_ELASTICSEARCH_TEST=1 to run')
def test_store_es_indicators_search_sort(store, token):
    x = store.handle_indicators_search(token, {
        'sort': '-confidence,lasttime,confidence', # intentionally try to sort by conf 2x
        'nolog': 1
    })
    x = json.loads(x)
    x = [i['_source'] for i in x['hits']['hits']]
    assert len(x) > 1

    for i in range(len(x)):
        if i != len(x) - 1: # make sure we're not comparing the last el in list
            # ensure confidence sorted DESC as specified in search sort param
            assert x[i]['confidence'] >= x[i+1]['confidence']
            # ensure lasttime secondary sorted ASC as specified in search sort param
            # secondary sort will only apply if primary sort field value was the same
            if x[i]['confidence'] == x[i+1]['confidence']:
                pprint(x[i])
                pprint(x[i+1])
                assert x[i]['lasttime'] <= x[i+1]['lasttime']

# normal searches (allowlists for feed pulls, upsert searches) should NOT find ssdeep relatives
@pytest.mark.skipif(DISABLE_TESTS, reason='need to set CIF_ELASTICSEARCH_TEST=1 to run')
def test_search_ssdeep_1_backend(store, token, indicator_ssdeep_1):
    search_filter = {
        'indicator': indicator_ssdeep_1.__dict__()['indicator'],
        'nolog': 1
    }
    x = store.handle_indicators_search(token, search_filter)
    x = json.loads(x)
    y = [i['_source'] for i in x['hits']['hits']]
    assert isinstance(y, list)
    assert len(y) == 1
    # ensure none of the other indicator submissions after ssdeep_1 matched on upsert search
    assert y[0]['count'] == 1

# normal frontend searches (HTTP GET /indicators) SHOULD find ssdeep relatives
@pytest.mark.skipif(DISABLE_TESTS, reason='need to set CIF_ELASTICSEARCH_TEST=1 to run')
def test_search_ssdeep_1_frontend(store, token, indicator_ssdeep_1, indicator_ssdeep_3):
    indicator = indicator_ssdeep_1.__dict__()['indicator']
    search_filter = {
        'indicator': indicator,
        'nolog': 1,
        'find_relatives': True
    }
    x = store.handle_indicators_search(token, search_filter)
    x = json.loads(x)
    y = [i['_source'] for i in x['hits']['hits']]
    assert isinstance(y, list)
    pprint(y)
    # ensure there are 2 results: 1 identical match and 1 fuzzy match
    assert len(y) == 2

    # ensure it didn't fuzzy match ssdeep_3
    for i in y:
        assert i['indicator'] is not indicator_ssdeep_3.__dict__()['indicator']
