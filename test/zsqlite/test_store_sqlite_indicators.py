import logging
import os
import tempfile
from argparse import Namespace
import pytest
from cif.store import Store
from cifsdk.utils import setup_logging
from sqlalchemy.ext.declarative import declarative_base
import arrow
from datetime import datetime
from pprint import pprint
from cifsdk.exceptions import AuthError
from csirtg_indicator.exceptions import InvalidIndicator

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
def indicator():
    return {
        'indicator': 'example.com',
        'tags': 'botnet',
        'provider': 'csirtgadgets.org',
        'group': 'everyone',
        'lasttime': arrow.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
        'itype': 'fqdn',
        'confidence': 6
    }


def test_store_sqlite_indicators(store, indicator):
    t = store.store.tokens.admin_exists()
    assert t

    t = list(store.store.tokens.search({'token': t}))
    assert len(t) > 0

    t = t[0]

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
    indicator['itype'] = 'ipv4'
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
    indicator['itype'] = 'ipv6'
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

    assert (x is None or x == 1)

    indicator['tags'] = 'malware'

    del indicator['group']
    try:
        x = store.handle_indicators_create(t, indicator)
    except InvalidIndicator:
        pass

    assert (x is None or x == 1)

    r = store.handle_indicators_delete(t, data=[{
        'indicator': 'example.com',
    }])
    assert r == 2

    x = store.handle_indicators_search(t, {
        'indicator': 'example.com',
        'nolog': 1
    })
    assert len(x) == 0

    x = store.handle_indicators_search(t, {
        'indicator': 'example2.com',
        'nolog': 1
    })

    for xx in x:
        r = store.handle_indicators_delete(t, data=[{
            'id': xx['id']
        }])
        assert r == 1

    indicator['indicator'] = 'd52380918a07322c50f1bfa2b43af3bb54cb33db'
    indicator['group'] = 'everyone'
    indicator['itype'] = 'sha1'

    x = store.handle_indicators_create(t, indicator)
    assert x > 0

    x = store.handle_indicators_search(t, {
        'indicator': indicator['indicator'],
        'nolog': 1
    })
    assert len(x) == 1
