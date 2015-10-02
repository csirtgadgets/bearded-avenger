import py.test

from cif.storage import Storage
from cif.utils import setup_logging
import logging
from argparse import Namespace
from pprint import pprint
import tempfile
import os

args = Namespace(debug=True, verbose=None)
setup_logging(args)

logger = logging.getLogger(__name__)


def test_storage():
    with Storage(store='dummy') as s:
        x = s.handle_search('1234', {'observable': 'example.com'})
        assert x[0]['observable'] == 'example.com'

        x = s.handle_submission('1234', {'observable': 'example.com'})
        assert x[0]['observable'] == 'example.com'


def test_storage_sqlite():
    dbfile = tempfile.mktemp()
    with Storage(store='sqlite', dbfile=dbfile) as s:
        logger.info('starting')
        x = s.handle_submission('1234', [
            {'observable': 'example.com', 'tags': ['botnet']},
            {'observable': 'example2.com', 'tags': ['malware']}
        ])

        assert x > 0

        x = s.handle_search('1234', {
            'observable': 'example.com'
        })

        pprint(x)

    os.unlink(dbfile)

