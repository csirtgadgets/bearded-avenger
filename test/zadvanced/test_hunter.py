import py.test

from cif.hunter import Hunter
from zmq.eventloop import ioloop
import threading
import tempfile
from pprint import pprint
import time

loop = ioloop.IOLoop.instance()
ADDR = 'ipc://{}'.format(tempfile.NamedTemporaryFile().name)


def test_zadvanced_hunter_start():
    with Hunter(loop=loop, remote=ADDR) as h:
        h = Hunter(loop=loop, remote=ADDR)

        t = threading.Thread(target=h.start)

        t.start()

        assert t.is_alive()

        loop.stop()

        t.join()

        assert not t.is_alive()
