import logging
import os
import tempfile
from argparse import Namespace
import pytest
from cif.store import Store
from cifsdk.utils import setup_logging
from csirtg_indicator.exceptions import InvalidIndicator
import arrow
from datetime import datetime
from pprint import pprint
from cifsdk.exceptions import AuthError

args = Namespace(debug=True, verbose=None)
setup_logging(args)

logger = logging.getLogger(__name__)


@pytest.yield_fixture
def store():
    dbfile = tempfile.mktemp()
    with Store(store_type='sqlite', dbfile=dbfile) as s:
        s._load_plugin(dbfile=dbfile)
        yield s

    if os.path.isfile(dbfile):
        os.unlink(dbfile)


@pytest.fixture
def indicator():
    return {
        'indicator': 'example.com',
        'tags': 'botnet',
        'provider': 'csirtgadgets.org',
        'group': 'everyone',
        'lasttime': arrow.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
        'itype': 'fqdn',
    }


def test_store_dummy(indicator):
    with Store(store_type='dummy') as s:
        t = s.store.tokens.admin_exists()

        x = s.handle_indicators_search(indicator)
        assert x[0]['indicator'] == 'example.com'

        x = s.handle_indicators_create(dict(indicator))
        assert x[0]['indicator'] == 'example.com'


def test_store_sqlite(store, indicator):
    store.token_create_admin()
    t = store.store.tokens.admin_exists()
    assert t

    t = list(store.store.tokens.search({'token': t}))
    assert len(t) > 0

    t = t[0]['token']

    assert store.store.tokens.update_last_activity_at(t, datetime.now())
    assert store.store.tokens.check(t, 'read')
    assert store.store.tokens.read(t)
    assert store.store.tokens.write(t)
    assert store.store.tokens.admin(t)
    assert store.store.tokens.last_activity_at(t) is not None
    assert store.store.tokens.update_last_activity_at(t, datetime.now())

    indicator['tags'] = 'malware'

    x = store.handle_indicators_create(t, indicator)

    assert x > 0

    indicator['lasttime'] = arrow.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ')

    x = store.handle_indicators_create(t, indicator)

    assert x == 1

    x = store.handle_indicators_search(t, {
        'indicator': 'example.com',
    })

    assert len(list(x)) > 0

    indicator['tags'] = 'botnet'
    indicator['indicator'] = 'example2.com'

    x = store.handle_indicators_create(t, indicator)

    assert x > 0

    x = store.handle_indicators_search(t, {
        'indicator': 'example2.com',
    })

    assert len(list(x)) > 0

    x = store.handle_indicators_search(t, {
        'indicator': 'example2.com',
        'tags': 'malware'
    })

    assert len(x) == 0

    indicator['indicator'] = '192.168.1.1'
    indicator['tags'] = 'botnet'

    x = store.handle_indicators_create(t, indicator)

    assert x > 0

    x = store.handle_indicators_search(t, {
        'indicator': '192.168.1.1',
    })

    assert len(list(x)) > 0

    x = store.handle_indicators_search(t, {
        'indicator': '192.168.1.0/24',
    })

    assert len(list(x)) > 0

    indicator['indicator'] = '2001:4860:4860::8888'
    indicator['tags'] = 'botnet'

    x = store.handle_indicators_create(t, indicator)

    assert x > 0

    x = store.handle_indicators_search(t, {
        'indicator': '2001:4860:4860::8888',
    })

    assert len(list(x)) > 0

    x = store.handle_indicators_search(t, {
        'indicator': '2001:4860::/32',
    })

    assert len(list(x)) > 0

    del indicator['tags']

    x = None

    try:
        x = store.handle_indicators_create(t, indicator)
    except InvalidIndicator:
        pass

    assert x is None

    indicator['tags'] = 'malware'

    del indicator['group']
    try:
        x = store.handle_indicators_create(t, indicator)
    except InvalidIndicator:
        pass

    assert x is None

    assert store.store.tokens.edit({'token': t, 'write': False})
    assert store.store.tokens.delete({'token': t})

    # groups
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
    assert not t['admin']

    i = None
    try:
        i = store.store.indicators.create(t, {
            'indicator': 'example.com',
            'group': 'staff2',
            'provider': 'example.com',
            'tags': ['test'],
            'itype': 'fqdn'
        })
    except AuthError as e:
        pass

    assert i is None

    i = store.store.indicators.create(t, {
        'indicator': 'example.com',
        'group': 'staff',
        'provider': 'example.com',
        'tags': ['test'],
        'itype': 'fqdn'
    })

    assert i

    x = store.store.indicators.search(t, {'indicator': 'example.com'})
    assert len(list(x)) > 0

    x = store.store.indicators.search(t, {'itype': 'fqdn'})
    assert len(list(x)) > 0
