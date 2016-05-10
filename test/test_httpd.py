import pytest

from cif import httpd, router
from pprint import pprint
import threading

# http://stackoverflow.com/a/34843029
import tempfile
import os
from zmq.eventloop import ioloop
ROUTER_ADDR = 'ipc://{}'.format(tempfile.NamedTemporaryFile().name)
router_loop = ioloop.IOLoop.instance()

@pytest.fixture
def client(request):
    httpd.app.config['TESTING'] = True
    httpd.app.config['CIF_ROUTER_ADDR'] = ROUTER_ADDR
    return httpd.app.test_client()


# http://bitterjug.com/blog/deadlock-bdd-testing-a-python-tornado-app-with-py-test-and-splinter/
def _router_start():
    r = router.Router(listen=ROUTER_ADDR)
    global router_thread
    router_thread = threading.Thread(target=r.run, args=[router_loop])
    router_thread.start()
    return True


def _router_stop():
    global router_thread
    router_loop.stop()
    router_thread.join()


@pytest.yield_fixture
def myrouter():
    yield _router_start()
    _router_stop()


def test_httpd_help(client):
    rv = client.get('/')
    assert b'{\n  "GET /": "this message", \n  "GET /help": "this message"' in rv.data


def test_httpd_ping(myrouter, client):
    rv = client.get('/ping')
    assert rv.status_code == 401

    rv = client.get('/ping', headers={'Authorization': 'Token token=1234'})
    assert rv.status_code == 200