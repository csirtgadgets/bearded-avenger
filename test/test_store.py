import logging
import os
import tempfile
from argparse import Namespace

import py.test

from cif.store import Store
from cif.utils import setup_logging
from csirtg_indicator import Indicator

args = Namespace(debug=True, verbose=None)
setup_logging(args)

logger = logging.getLogger(__name__)


@py.test.yield_fixture
def store():
    dbfile = tempfile.mktemp()
    with Store(store='sqlite', dbfile=dbfile) as s:
        yield s

    os.unlink(dbfile)


@py.test.fixture
def obs():
    return Indicator(indicator='example.com', tags=['botnet'], provider='csirtgadgets.org')


def test_store_dummy(obs):
    with Store(store='dummy') as s:
        t = s.store.tokens_admin_exists()

        x = s.handle_indicators_search(t, obs.__dict__)
        assert x[0]['indicator'] == 'example.com'

        x = s.handle_indicators_create(t, obs.__dict__)
        assert x[0]['indicator'] == 'example.com'


def test_store_sqlite(store):
    store.token_create_admin()
    t = store.store.tokens_admin_exists()
    assert t

    i = [
        Indicator(indicator='example.com', tags='botnet', provider='csirtgadgets.org').__dict__,
        Indicator(indicator='example2.com', tags='malware', provider='csirtgadgets.org').__dict__
    ]

    x = store.handle_indicators_create(t, {
        'indicator': 'example.com'
    })
    assert x > 0

    x = store.handle_indicators_search(t, {
        'indicator': 'example.com'
    })

    assert x > 0
