import json
import os
import tempfile

import pytest
from cif import httpd
from cif.store import Store
from zmq.eventloop import ioloop

from cifsdk.constants import PYVERSION

ROUTER_ADDR = 'ipc://{}'.format(tempfile.NamedTemporaryFile().name)
router_loop = ioloop.IOLoop.instance()

@pytest.fixture
def client(request):
    httpd.app.config['TESTING'] = True
    httpd.app.config['CIF_ROUTER_ADDR'] = ROUTER_ADDR
    httpd.app.config['dummy'] = True
    return httpd.app.test_client()


@pytest.yield_fixture
def store():
    dbfile = tempfile.mktemp()
    with Store(store_type='sqlite', dbfile=dbfile) as s:
        yield s

    os.unlink(dbfile)


def test_httpd_help(client):
    rv = client.get('/')
    assert rv.status_code == 200

    rv = client.get('/help')
    assert rv.status_code == 200


def test_httpd_ping(client):
    rv = client.get('/ping')
    assert rv.status_code == 401

    rv = client.get('/ping', headers={'Authorization': 'Token token=1234'})
    assert rv.status_code == 200


def test_httpd_search(client):
    rv = client.get('/search?q=example.com', headers={'Authorization': 'Token token=1234'})
    assert rv.status_code == 200

    data = rv.data
    if PYVERSION > 2:
        data = data.decode('utf-8')

    rv = json.loads(data)
    assert rv['data'][0]['indicator'] == 'example.com'


def test_httpd_indicators(client):
    rv = client.get('/indicators?q=example.com', headers={'Authorization': 'Token token=1234'})
    assert rv.status_code == 200

    data = rv.data
    if PYVERSION > 2:
        data = data.decode('utf-8')

    rv = json.loads(data)
    assert rv['data'][0]['indicator'] == 'example.com'


def test_httpd_feed(client):
    rv = client.get('/feed?itype=fqdn&indicator=example.com&confidence=85', headers={'Authorization': 'Token token=1234'})

    assert rv.status_code == 200


def test_httpd_tokens(client):
    rv = client.get('/tokens', headers={'Authorization': 'Token token=1234'})
    assert rv.status_code == 200