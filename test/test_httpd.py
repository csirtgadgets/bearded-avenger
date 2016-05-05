import pytest

#import cif.httpd as httpd
#import flaskr
from cif import httpd, router, storage
from cif.constants import REMOTE_ADDR, HUNTER_ADDR, STORAGE_ADDR
from pprint import pprint
import threading

# http://stackoverflow.com/a/34843029
from zmq.eventloop import ioloop
loop = ioloop.IOLoop.instance()
@pytest.fixture
def client(request):
    httpd.app.config['TESTING'] = True
    return httpd.app.test_client()


# http://bitterjug.com/blog/deadlock-bdd-testing-a-python-tornado-app-with-py-test-and-splinter/
def _router_start():
    r = router.Router()
    global thread
    thread = threading.Thread(target=r.run, args=[loop])
    thread.start()
    return True


def _router_stop():
    global thread
    loop.stop()
    thread.join()


def _storage():
    s = storage.Store()
    thread = threading.Thread(target=s.start)
    thread.start()
    return True

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
