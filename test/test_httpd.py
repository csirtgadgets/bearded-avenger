import tempfile

import pytest
from cif import httpd
from zmq.eventloop import ioloop
ROUTER_ADDR = 'ipc://{}'.format(tempfile.NamedTemporaryFile().name)
router_loop = ioloop.IOLoop.instance()

@pytest.fixture
def client(request):
    httpd.app.config['TESTING'] = True
    httpd.app.config['CIF_ROUTER_ADDR'] = ROUTER_ADDR
    httpd.app.config['dummy'] = True
    return httpd.app.test_client()


def test_httpd_help(client):
    rv = client.get('/')
    assert rv.status_code == 200


def test_httpd_ping(client):
    rv = client.get('/ping')
    assert rv.status_code == 401

    rv = client.get('/ping', headers={'Authorization': 'Token token=1234'})
    assert rv.status_code == 200


def test_httpd_search(client):

    rv = client.get('/search', {'indicator': 'example.com'}, headers={'Authorization': 'Token token=1234'})
    assert rv.status_code == 200


def test_httpd_search_v2(client):
    rv = client.get('/observables',
                    {'observable': 'example.com'},
                    headers={'Authorization': 'Token token=1234', 'Accept': 'vnd.cif.v2+json'})
    assert rv.status_code == 200