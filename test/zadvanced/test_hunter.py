import pytest

from cif.hunter import Hunter
from tornado.ioloop import IOLoop
import threading
import tempfile
import os

loop = IOLoop()
ADDR = 'ipc://{}'.format(tempfile.NamedTemporaryFile().name)


@pytest.mark.skipif(not os.environ.get('CIF_ADVANCED_TESTS'), reason='requires CIF_ADVANCED_TEST to be true')
def test_zadvanced_hunter_start():
    with Hunter(loop=loop, remote=ADDR) as h:
        h = Hunter(loop=loop, remote=ADDR)

        t = threading.Thread(target=h.start)

        t.start()

        assert t.is_alive()

        loop.stop()

        t.join()

        assert not t.is_alive()
