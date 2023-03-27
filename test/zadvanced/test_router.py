import pytest
import threading
from cif.router import Router
from cif.constants import ROUTER_ADDR
from tornado.ioloop import IOLoop
import tempfile

loop = IOLoop()

ROUTER_ADDR = 'ipc://{}'.format(tempfile.NamedTemporaryFile().name)


def _router_start():
    r = Router(listen=ROUTER_ADDR)
    global thread
    thread = threading.Thread(target=r.run, args=[loop])
    thread.start()
    return True


def _router_stop():
    global thread
    loop.stop()
    thread.join()


@pytest.fixture
def router():
    yield _router_start()
    _router_stop()


@pytest.fixture
def client():
    from cif.client.zeromq import ZMQ as Client

    yield Client(ROUTER_ADDR, '1234')
