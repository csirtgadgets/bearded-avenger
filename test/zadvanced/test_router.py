import pytest
import threading
from pprint import pprint
from cif.router import Router
from cif.constants import ROUTER_ADDR
from zmq.eventloop import ioloop
import tempfile

loop = ioloop.IOLoop.instance()

ROUTER_ADDR = 'ipc://{}'.format(tempfile.NamedTemporaryFile().name)


def _router_start():
    print ROUTER_ADDR
    r = Router(listen=ROUTER_ADDR)
    global thread
    thread = threading.Thread(target=r.run, args=[loop])
    thread.start()
    return True


def _router_stop():
    global thread
    loop.stop()
    thread.join()


@pytest.yield_fixture
def router():
    yield _router_start()
    _router_stop()


@pytest.yield_fixture
def client():
    from cif.client.zeromq import ZMQ as Client

    yield Client(ROUTER_ADDR, '1234')
