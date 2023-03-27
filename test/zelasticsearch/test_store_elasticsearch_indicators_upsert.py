import pytest
from csirtg_indicator import Indicator
from elasticsearch_dsl.connections import connections
from cif.store import Store
import os
import arrow
import ujson as json
from pprint import pprint

DISABLE_TESTS = True
if os.environ.get('CIF_ELASTICSEARCH_TEST') and os.environ.get('CIF_STORE_ES_UPSERT_MODE'):
    if os.environ['CIF_ELASTICSEARCH_TEST'] == '1' and os.environ['CIF_STORE_ES_UPSERT_MODE'] == '1':
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
        'username': 'test_admin',
        'groups': ['everyone', 'everyone2'],
        'read': '1',
        'write': '1',
        'admin': '1'
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

# testing upsert matches w/ additional fields like application, portlist, and protocol
@pytest.fixture
def indicator5():
    return Indicator(
        indicator='example.com',
        tags=['scanner', 'bruteforce'],
        provider='test-provider',
        group='everyone',
        lasttime=arrow.utcnow().datetime,
        reporttime=arrow.utcnow().datetime,
        confidence=7.5,
        application='ssh',
        portlist='22,23',
        protocol='tcp',
        description='this is indicator5'
    )

# same as i5 but diff portlist
@pytest.fixture
def indicator5_diff_portlist():
    return Indicator(
        indicator='example.com',
        tags=['scanner', 'bruteforce'],
        provider='test-provider',
        group='everyone',
        lasttime=arrow.utcnow().datetime,
        reporttime=arrow.utcnow().datetime,
        confidence=7.5,
        application='ssh',
        portlist='25',
        protocol='tcp',
        description='this is indicator5 w/ a diff portlist'
    )

# same as i5 but different protocol
@pytest.fixture
def indicator5_diff_protocol():
    return Indicator(
        indicator='example.com',
        tags=['scanner', 'bruteforce'],
        provider='test-provider',
        group='everyone',
        lasttime=arrow.utcnow().datetime,
        reporttime=arrow.utcnow().datetime,
        confidence=7.5,
        application='ssh',
        portlist='22,23',
        description='this is indicator5 w/ diff protocol',
        protocol='udp'
    )

# same as indicator but lower conf
@pytest.fixture
def indicator_lower_conf():
    return Indicator(
        indicator='example.com',
        tags='botnet',
        provider='csirtg.io',
        group='everyone',
        lasttime=arrow.utcnow().datetime,
        reporttime=arrow.utcnow().datetime,
        confidence=6.0
    )

# same as indicator but higher conf
@pytest.fixture
def indicator_higher_conf():
    return Indicator(
        indicator='example.com',
        tags='botnet',
        provider='csirtg.io',
        group='everyone',
        lasttime=arrow.utcnow().datetime,
        reporttime=arrow.utcnow().datetime,
        confidence=8.0
    )

@pytest.fixture
def indicator_diff_group():
    return Indicator(
        indicator='example.com',
        tags='botnet',
        provider='csirtg.io',
        group='everyone2',
        lasttime=arrow.utcnow().datetime,
        reporttime=arrow.utcnow().datetime,
        confidence=7.0
    )

@pytest.fixture
def indicator_diff_rdata():
    return Indicator(
        indicator='example.com',
        tags='botnet',
        provider='csirtg.io',
        group='everyone',
        lasttime=arrow.utcnow().datetime,
        reporttime=arrow.utcnow().datetime,
        confidence=7.0,
        rdata='ns 10.1.1.1'
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


## test duplicate indicator submission, different confidence; ensure upserts are NOT matching on diff confidence, lower or higher
@pytest.mark.skipif(DISABLE_TESTS, reason='need to set CIF_ELASTICSEARCH_TEST=1 to run')
def test_store_elasticsearch_indicators_upsert6(store, token, indicator, indicator_lower_conf, indicator_higher_conf):

    pprint(indicator)

    x = store.handle_indicators_create(token, indicator.__dict__(), flush=True)
    assert x == 1

    pprint(indicator_lower_conf)

    y = store.handle_indicators_create(token, indicator_lower_conf.__dict__(), flush=True)
    assert y == 1

    pprint(indicator_higher_conf)

    z = store.handle_indicators_create(token, indicator_higher_conf.__dict__(), flush=True)
    assert z == 1

    x = store.handle_indicators_search(token, {
        'indicator': 'example.com',
        'nolog': 1
    })

    x = json.loads(x)
    x = [i['_source'] for i in x['hits']['hits']]

    pprint(x)

    assert len(x) == 3


## test similar indicator submissions, but different portlist and/or protocol; ensure upserts are NOT matching on differences and creating unique indicators
@pytest.mark.skipif(DISABLE_TESTS, reason='need to set CIF_ELASTICSEARCH_TEST=1 to run')
def test_store_elasticsearch_indicators_upsert7(store, token, indicator5, indicator5_diff_portlist, indicator5_diff_protocol):

    pprint(indicator5)

    x = store.handle_indicators_create(token, indicator5.__dict__(), flush=True)
    assert x == 1

    pprint(indicator5_diff_portlist)

    y = store.handle_indicators_create(token, indicator5_diff_portlist.__dict__(), flush=True)
    assert y == 1

    pprint(indicator5_diff_protocol)

    z = store.handle_indicators_create(token, indicator5_diff_protocol.__dict__(), flush=True)
    assert z == 1

    x = store.handle_indicators_search(token, {
        'indicator': 'example.com',
        'nolog': 1
    })

    x = json.loads(x)
    x = [i['_source'] for i in x['hits']['hits']]

    pprint(x)

    assert len(x) == 3

    # store a duplicate and ensure overall search result counts don't change
    z = store.handle_indicators_create(token, indicator5_diff_protocol.__dict__(), flush=True)
    assert z == 0

    x = store.handle_indicators_search(token, {
        'indicator': 'example.com',
        'nolog': 1
    })

    x = json.loads(x)
    x = [i['_source'] for i in x['hits']['hits']]

    pprint(x)

    assert len(x) == 3

## test duplicate indicator submission, different groups; 
# ensure upserts are NOT matching on diff groups
@pytest.mark.skipif(DISABLE_TESTS, reason='need to set CIF_ELASTICSEARCH_TEST=1 to run')
def test_store_elasticsearch_indicators_upsert8(store, token, indicator, indicator_diff_group):

    pprint(indicator)

    indicator_dict = indicator.__dict__()

    x = store.handle_indicators_create(token, indicator_dict, flush=True)
    assert x == 1

    pprint(indicator_diff_group)

    y = store.handle_indicators_create(token, indicator_diff_group.__dict__(), flush=True)
    assert y == 1

    x = store.handle_indicators_search(token, {
        'indicator': 'example.com',
        'nolog': 1
    })

    z = json.loads(x)
    z = [i['_source'] for i in z['hits']['hits']]

    pprint(z)

    assert len(z) == 2

    # refresh 1st indicator times and resubmit to upsert/increase count
    # ensure it doesn't upsert into 2nd indicator (that has the same tag but one additional)
    indicator_dict['lasttime'] = indicator_dict['reporttime'] = arrow.utcnow().datetime
    new_observation = Indicator(**indicator_dict)

    x = store.handle_indicators_create(token, new_observation.__dict__(), flush=True)
    assert x == 1

    y = store.handle_indicators_search(token, {
        'indicator': 'example.com',
        'nolog': 1
    })

    z = json.loads(y)
    z = [i['_source'] for i in z['hits']['hits']]

    assert len(z) == 2 # should still have 2 indicators, but should have upserted into 1st

    pprint(z)

    for i in z:
        # orig indicator should have upsert matched once for a total count of 2
        if i['group'] == 'everyone' or 'everyone' in i['group']: # group = 'everyone' or ['everyone']
            assert i['count'] == 2
        # the indicator with group 'everyone2' should only have a count of 1
        else:
            assert i['count'] == 1

## test duplicate indicator submission, different rdata; 
# ensure upserts are NOT matching on diff rdata
@pytest.mark.skipif(DISABLE_TESTS, reason='need to set CIF_ELASTICSEARCH_TEST=1 to run')
def test_store_elasticsearch_indicators_upsert9(store, token, indicator, indicator_diff_rdata):

    pprint(indicator)

    indicator_dict = indicator.__dict__()

    x = store.handle_indicators_create(token, indicator_dict, flush=True)
    assert x == 1

    pprint(indicator_diff_group)

    indicator_rdata_dict = indicator_diff_rdata.__dict__()

    y = store.handle_indicators_create(token, indicator_rdata_dict, flush=True)
    assert y == 1

    x = store.handle_indicators_search(token, {
        'indicator': 'example.com',
        'nolog': 1
    })

    z = json.loads(x)
    z = [i['_source'] for i in z['hits']['hits']]

    pprint(z)

    assert len(z) == 2

    # refresh 1st indicator times and resubmit to upsert/increase count
    # ensure it doesn't upsert into 2nd indicator (that has the same tag but one additional)
    indicator_dict['lasttime'] = indicator_dict['reporttime'] = arrow.utcnow().datetime
    new_observation = Indicator(**indicator_dict)

    x = store.handle_indicators_create(token, new_observation.__dict__(), flush=True)
    assert x == 1

    y = store.handle_indicators_search(token, {
        'indicator': 'example.com',
        'nolog': 1
    })

    z = json.loads(y)
    z = [i['_source'] for i in z['hits']['hits']]

    assert len(z) == 2 # should still have 2 indicators, but should have upserted into 1st

    pprint(z)

    for i in z:
        # orig indicator (w/o rdata) should have upsert matched once for a total count of 2
        if not i.get('rdata'):
            assert i['count'] == 2
        # the indicator with rdata (different) should only have a count of 1
        else:
            assert i['count'] == 1

    # refresh 2nd indicator times and resubmit to test upsert
    # ensure it doesn't upsert into 2nd indicator (that has the same rdata but
    # new observation contains an asterisk which should be ignored)
    indicator_rdata_dict['lasttime'] = indicator_rdata_dict['reporttime'] = arrow.utcnow().datetime
    indicator_rdata_dict['rdata'] = 'some*test'
    new_rdata_observation = Indicator(**indicator_rdata_dict)

    x = store.handle_indicators_create(token, new_rdata_observation.__dict__(), flush=True)
    assert x == 1

    y = store.handle_indicators_search(token, {
        'indicator': 'example.com',
        'nolog': 1
    })

    z = json.loads(y)
    z = [i['_source'] for i in z['hits']['hits']]

    assert len(z) == 2 # should still have 2 indicators, but latest should have upserted into 1st

    pprint(z)

    for i in z:
        # orig indicator (w/o rdata) should have upsert matched twice now for a total count of 3
        if not i.get('rdata'):
            assert i['count'] == 3
        # the indicator with rdata (different) should only have a count of 1
        else:
            assert i['count'] == 1
