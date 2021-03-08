import logging
import os
import tempfile
from argparse import Namespace
import pytest
from cif.store import Store
from cifsdk.utils import setup_logging
import arrow
from datetime import datetime
from pprint import pprint
from cifsdk.exceptions import AuthError

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
    }


def test_store_sqlite_tokens(store):
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


def test_store_sqlite_tokens_groups(store):
    t = store.store.tokens.admin_exists()
    assert t
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

    assert i == 0

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


def test_store_sqlite_tokens_groups2(store, indicator):
    t = store.store.tokens.create({
        'username': 'test',
        'groups': ['staff'],
        'read': True,
        'write': True
    })

    i = None
    try:
        i = store.store.indicators.create(t, {
            'indicator': 'example.com',
            'group': 'staff2',
            'provider': 'example.com',
            'tags': ['test'],
            'itype': 'fqdn',
            'lasttime': arrow.utcnow().datetime,
            'reporttime': arrow.utcnow().datetime

        })
    except AuthError as e:
        pass

    assert (i is None or i == 0)


def test_store_sqlite_tokens_groups3(store, indicator):
    t = store.store.tokens.create({
        'username': 'test',
        'groups': ['staff'],
        'write': True
    })

    t2 = store.store.tokens.create({
        'username': 'test',
        'groups': ['staff2'],
        'read': True,
    })

    i = store.store.indicators.create(t, {
        'indicator': 'example.com',
        'group': 'staff',
        'provider': 'example.com',
        'tags': ['test'],
        'itype': 'fqdn',
        'lasttime': arrow.utcnow().datetime,
        'reporttime': arrow.utcnow().datetime

    })

    assert i

    i = store.store.indicators.search(t2, {'itype': 'fqdn'})
    assert len(list(i)) == 0

    i = store.store.indicators.search(t2, {'indicator': 'example.com'})
    assert len(list(i)) == 0


def test_store_sqlite_tokens_groups4(store, indicator):
    t = store.store.tokens.create({
        'username': 'test',
        'groups': ['staff', 'staff2'],
        'write': True,
        'read': True
    })

    i = store.store.indicators.create(t, {
        'indicator': 'example.com',
        'group': 'staff',
        'provider': 'example.com',
        'tags': ['test'],
        'itype': 'fqdn',
        'lasttime': arrow.utcnow().datetime,
        'reporttime': arrow.utcnow().datetime

    })

    assert i

    i = store.store.indicators.create(t, {
        'indicator': 'example.com',
        'group': 'staff2',
        'provider': 'example.com',
        'tags': ['test'],
        'itype': 'fqdn',
        'lasttime': arrow.utcnow().datetime,
        'reporttime': arrow.utcnow().datetime

    })

    assert i

    i = store.store.indicators.search(t['token'], {'itype': 'fqdn', 'groups': 'staff'})
    assert len(list(i)) == 1