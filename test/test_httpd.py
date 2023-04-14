import ujson as json
import os
import tempfile

import pytest
from cif import httpd
from cif.store import Store

from cifsdk.constants import PYVERSION

ROUTER_ADDR = 'ipc://{}'.format(tempfile.NamedTemporaryFile().name)

@pytest.fixture
def client(request):
    httpd.app.config['TESTING'] = True
    httpd.app.config['CIF_ROUTER_ADDR'] = ROUTER_ADDR
    httpd.app.config['dummy'] = True
    return httpd.app.test_client()


@pytest.fixture
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


def test_httpd_confidence(client):
    rv = client.get('/help/confidence')
    assert rv.status_code == 200

    rv = client.get('/help/confidence', headers={'Authorization': 'Token token=1234'})
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
    import arrow
    httpd.app.config['feed'] = {}
    httpd.app.config['feed']['data'] = [
        {
            'indicator': '128.205.1.1',
            'confidence': '8',
            'tags': ['malware'],
            'reporttime': str(arrow.utcnow()),
        },
        {
            'indicator': '128.205.2.1',
            'confidence': '8',
            'tags': ['malware'],
            'reporttime': str(arrow.utcnow()),
        },
    ]
    httpd.app.config['feed']['wl'] = [
        {
            'indicator': '128.205.0.0/16',
            'confidence': '8',
            'tags': ['whitelist'],
            'reporttime': str(arrow.utcnow()),
        },
    ]

    rv = client.get('/feed?itype=ipv4&confidence=7', headers={'Authorization': 'Token token=1234'})

    assert rv.status_code == 200

    r = json.loads(rv.data.decode('utf-8'))
    assert len(r['data']) == 0

def test_httpd_feed_fqdn(client):
    import arrow
    httpd.app.config['feed'] = {}
    httpd.app.config['feed']['data'] = [
        {
            'indicator': 'page-test.weebly.com',
            'confidence': '8',
            'tags': ['malware'],
            'reporttime': str(arrow.utcnow()),
        },
        {
            'indicator': 'example.com',
            'confidence': '8',
            'tags': ['malware'],
            'reporttime': str(arrow.utcnow()),
        },
        {
            'indicator': 'test.google.com',
            'confidence': '8',
            'tags': ['malware'],
            'reporttime': str(arrow.utcnow()),
        },
        {
            'indicator': 'test.test.ex.com',
            'confidence': '8',
            'tags': ['malware'],
            'reporttime': str(arrow.utcnow()),
        },
    ]
    httpd.app.config['feed']['wl'] = [
        {
            'indicator': 'ex.com',
            'confidence': '8',
            'tags': ['whitelist'],
            'reporttime': str(arrow.utcnow()),
        },
    ]

    rv = client.get('/feed?itype=fqdn&confidence=7', headers={'Authorization': 'Token token=1234'})

    assert rv.status_code == 200

    r = json.loads(rv.data.decode('utf-8'))
    assert len(r['data']) == 1


def test_httpd_tokens(client):
    rv = client.get('/tokens', headers={'Authorization': 'Token token=1234'})
    assert rv.status_code == 200