import py.test

from cif.hunter import Hunter
from zmq.eventloop import ioloop
import threading
import tempfile
from pprint import pprint
import time

loop = ioloop.IOLoop.instance()
ADDR = 'ipc://{}'.format(tempfile.NamedTemporaryFile().name)


def test_hunter():
    with Hunter() as h:
        assert isinstance(h, Hunter)


def test_hunter_start():
    h = Hunter(loop=loop, remote=ADDR)

    t = threading.Thread(target=h.start)

    t.start()
    assert t.is_alive()

    loop.stop()

    t.join()

    time.sleep(0.1)

    assert not t.is_alive()
