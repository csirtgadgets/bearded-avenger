import logging
import os
import tempfile
from argparse import Namespace
import pytest
from cif.store import Store
from cifsdk.utils import setup_logging
import arrow

args = Namespace(debug=True, verbose=None)
setup_logging(args)

logger = logging.getLogger(__name__)


@pytest.fixture
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
