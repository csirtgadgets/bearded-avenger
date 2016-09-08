import logging
import os
import tempfile
from argparse import Namespace

import py.test

from cif.store import Store
from cifsdk.utils import setup_logging
from csirtg_indicator import Indicator
from cifsdk.constants import PYVERSION

args = Namespace(debug=True, verbose=None)
setup_logging(args)

logger = logging.getLogger(__name__)


@py.test.yield_fixture
def store():
    dbfile = tempfile.mktemp()
    with Store(store_type='sqlite', dbfile=dbfile) as s:
        yield s

    os.unlink(dbfile)


@py.test.fixture
def obs():
    return {
        'indicator': 'example.com',
        'tags': ['botnet'],
        'provider': 'csirtgadgets.org'
    }


def test_store_dummy(obs):
    with Store(store_type='dummy') as s:
        t = s.store.tokens_admin_exists()

        x = s.handle_indicators_search(obs)
        assert x[0]['indicator'] == 'example.com'

        x = s.handle_indicators_create(dict(obs))
        assert x[0]['indicator'] == 'example.com'


def test_store_sqlite(store):
    store.token_create_admin()
    t = store.store.tokens_admin_exists()
    assert t

    x = store.handle_indicators_create(t, {
        'indicator': 'example.com',
        'tags': 'malware',
        'provider': 'csirtgadgets.org',
    })

    assert x > 0

    x = store.handle_indicators_search(t, {
        'indicator': 'example.com',
    })

    x = store.handle_indicators_create(t, {
        'indicator': 'example2.com',
        'tags': 'botnet',
        'provider': 'csirtgadgets.org',
    })

    assert x > 0

    x = store.handle_indicators_search(t, {
        'indicator': 'example2.com',
    })

    assert len(x) > 0

    x = store.handle_indicators_search(t, {
        'indicator': 'example2.com',
        'tags': 'malware'
    })

    assert len(x) == 0

    x = store.handle_indicators_create(t, {
        'indicator': '192.168.1.1',
        'tags': 'botnet',
        'provider': 'csirtgadgets.org',
    })

    assert x > 0

    x = store.handle_indicators_search(t, {
        'indicator': '192.168.1.1',
    })

    assert len(x) > 0

    x = store.handle_indicators_search(t, {
        'indicator': '192.168.1.0/24',
    })

    assert len(x) > 0

