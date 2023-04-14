import pytest
from csirtg_indicator import Indicator
from cif.store import Store
from elasticsearch_dsl.connections import connections
import os
import arrow
from time import sleep
from pprint import pprint

DISABLE_TESTS = True
if os.environ.get('CIF_ELASTICSEARCH_TEST', '0') == '1':
    DISABLE_TESTS = False


@pytest.fixture
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
def user_token(store):
    t = store.store.tokens.create({
        'username': u'test_user',
        'groups': [u'everyone'],
        'read': u'1',
        'write': False,
        'admin': False
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
def test_store_elasticsearch_tokens_edit_groups(store, token):

    x = store.handle_tokens_search(token, {'token': token['token']})
    x = list(x)

    pprint(x)

    assert x[0]['groups'] == ['everyone']

    u = {
        'token': token['token'],
        'groups': ['staff', 'everyone']
    }

    x = store.handle_tokens_edit(token, u)

    assert x

    x = store.handle_tokens_search(token, {'token': token['token']})
    x = list(x)

    pprint(x)

    assert x[0]['read']
    assert x[0]['write']
    assert x[0]['admin']
    assert x[0]['groups'] == ['staff', 'everyone']

@pytest.mark.skipif(DISABLE_TESTS, reason='need to set CIF_ELASTICSEARCH_TEST=1 to run')
def test_store_elasticsearch_tokens_edit_rw_perms(store, token):

    x = store.handle_tokens_search(token, {'token': token['token']})
    x = list(x)

    pprint(x)

    assert x[0]['read']
    assert x[0]['write']

    u = {
        'token': token['token'],
        'write': False
    }

    x = store.handle_tokens_edit(token, u)

    assert x

    x = store.handle_tokens_search(token, {'token': token['token']})
    x = list(x)

    pprint(x)

    assert x[0]['read']
    assert x[0]['admin']
    assert x[0]['groups'] == ['everyone']
    assert x[0]['write'] == False

@pytest.mark.skipif(DISABLE_TESTS, reason='need to set CIF_ELASTICSEARCH_TEST=1 to run')
def test_store_elasticsearch_tokens_edit_time_fields_with_cache(store, token, user_token):

    starttime = arrow.utcnow().datetime.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
    # do an auth search to cache user token data
    x = store.store.tokens.auth_search(user_token) 
    x = list(x)

    pprint(x)

    assert x[0]['groups'] == ['everyone']

    new_groups = ['staff', 'everyone']

    u = {
        'token': user_token['token'],
        'groups': new_groups
    }

    # a token edit will update the token cache then force immediate cache flush to ES
    x = store.handle_tokens_edit(token, u)

    assert x

    # provide enough time for cache to write-behind
    sleep(2)

    x = store.store.tokens.auth_search(user_token) 
    x = list(x)

    pprint(x)

    assert x[0]['read']
    assert not x[0]['write']
    assert not x[0]['admin']
    assert x[0]['groups'] == new_groups
    assert x[0]['last_activity_at']
    assert x[0]['last_activity_at'] > starttime
    assert x[0]['last_edited_by']
    assert x[0]['last_edited_by'] == 'test_admin'
    assert x[0]['last_edited_at']
    assert x[0]['last_edited_at'] > starttime
    assert x[0]['created_at']
    assert x[0]['created_at'] < starttime
