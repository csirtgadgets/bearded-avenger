import logging
import os
import tempfile
from argparse import Namespace
import pytest
from cif.store import Store
from cifsdk.utils import setup_logging
import arrow
from csirtg_indicator.exceptions import InvalidIndicator
import copy
from pprint import pprint

args = Namespace(debug=True, verbose=None)
setup_logging(args)

logger = logging.getLogger(__name__)

@pytest.fixture
def store():
    dbfile = tempfile.mktemp()
    with Store(store_type='sqlite', dbfile=dbfile) as s:
        s._load_plugin(dbfile=dbfile)
        s.token_create_admin()
        yield s

    s = None
    if os.path.isfile(dbfile):
        os.unlink(dbfile)

@pytest.fixture
def token(store):
    t = store.store.tokens.create({
        'username': u'test_sqlite_admin',
        'groups': [u'everyone'],
        'read': u'1',
        'write': u'1',
        'admin': u'1'
    })

    assert t
    yield t


@pytest.fixture
def indicator():
    now = arrow.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ')
    return {
        'indicator': 'example.com',
        'tags': 'botnet',
        'provider': 'csirtgadgets.org',
        'group': 'everyone',
        'lasttime': now,
        'itype': 'fqdn',
        'confidence': 6
    }


def test_store_indicators_search_reporttime(store, token, indicator):
    now = arrow.utcnow()
    now_str = now.datetime.strftime('%Y-%m-%dT%H:%M:%SZ')
    days_ago_arrow = now.shift(days=-5)
    days_ago_str = days_ago_arrow.datetime.strftime('%Y-%m-%dT%H:%M:%SZ')
    weeks_ago_str = now.shift(weeks=-3).datetime.strftime('%Y-%m-%dT%H:%M:%SZ')

    indicator['reporttime'] = indicator['lasttime'] = weeks_ago_str
    
    indicator_url = copy.deepcopy(indicator)
    indicator_url['indicator'] = 'https://example.com'
    indicator_url['reporttime'] = indicator_url['lasttime'] = days_ago_str
    
    indicator_alt_provider = copy.deepcopy(indicator)
    indicator_alt_provider['provider'] = 'csirtg.io'
    indicator_alt_provider['reporttime'] = indicator_alt_provider['lasttime'] = now_str

    x = store.handle_indicators_create(token, indicator, flush=True)
    assert x > 0

    y = store.handle_indicators_create(token, indicator_url, flush=True)
    assert y > 0

    z = store.handle_indicators_create(token, indicator_alt_provider, flush=True)
    assert z > 0

    x = store.handle_indicators_search(token, {
        'days': '6'
    })

    pprint(x)
    
    assert len(x) == 2

    for indicator in x:
        assert arrow.get(indicator['reporttime']) >= arrow.get(days_ago_str)

    start_str = weeks_ago_str
    end_str = days_ago_str
    startend = '{},{}'.format(start_str, end_str)

    y = store.handle_indicators_search(token, {
        'reporttime': startend
    })

    pprint(y)

    assert len(y) == 2

    for indicator in y:
        assert arrow.get(indicator['reporttime']) <= arrow.get(days_ago_str)
