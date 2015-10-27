import py.test

from cif.storage import Storage
from cif.utils import setup_logging
import logging
from argparse import Namespace
from pprint import pprint
import tempfile
import os
from cif.observable import Observable

args = Namespace(debug=True, verbose=None)
setup_logging(args)

logger = logging.getLogger(__name__)

@py.test.fixture
def obs():
    return Observable(observable='example.com', tags=['botnet'], provider='csirtgadgets.org')

def test_storage(obs):
    with Storage(store='dummy') as s:
        x = s.handle_search('1234', obs.__dict__)
        assert x[0]['observable'] == 'example.com'

        x = s.handle_submission('1234', obs.__dict__)
        assert x[0]['observable'] == 'example.com'


def test_storage_sqlite(obs):
    dbfile = tempfile.mktemp()
    with Storage(store='sqlite', dbfile=dbfile) as s:
        ob = [
            Observable(observable='example.com', tags=['botnet'], provider='csirtgadgets.org').__dict__,
            Observable(observable='example2.com', tags=['malware'], provider='csirtgadgets.org').__dict__
        ]
        x = s.handle_submission('1234', ob)

        assert x > 0

        x = s.handle_search('1234', {
            'observable': 'example.com'
        })

    os.unlink(dbfile)

