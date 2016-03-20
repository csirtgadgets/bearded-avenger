import logging
import os
import tempfile
from argparse import Namespace

import py.test

from cif.indicator import Indicator
from cif.storage import Storage
from cif.utils import setup_logging

args = Namespace(debug=True, verbose=None)
setup_logging(args)

logger = logging.getLogger(__name__)

@py.test.fixture
def obs():
    return Indicator(indicator='example.com', tags=['botnet'], provider='csirtgadgets.org')

def test_storage(obs):
    with Storage(store='dummy') as s:
        x = s.handle_search('1234', obs.__dict__)
        assert x[0]['indicator'] == 'example.com'

        x = s.handle_submission('1234', obs.__dict__)
        assert x[0]['indicator'] == 'example.com'


def test_storage_sqlite(obs):
    dbfile = tempfile.mktemp()
    with Storage(store='sqlite', dbfile=dbfile) as s:
        ob = [
            Indicator(indicator='example.com', tags=['botnet'], provider='csirtgadgets.org').__dict__,
            Indicator(indicator='example2.com', tags=['malware'], provider='csirtgadgets.org').__dict__
        ]
        x = s.handle_submission('1234', ob)

        assert x > 0

        x = s.handle_search('1234', {
            'indicator': 'example.com'
        })

    os.unlink(dbfile)

