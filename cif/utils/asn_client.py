import ujson as json
import logging
import sys
import zmq

logger = logging.getLogger(__name__)


class Timeout(Exception):
    pass


def chunk(it, slice=50):
    """Generate sublists from an iterator
    >>> list(chunk(iter(range(10)),11))
    [[0, 1, 2, 3, 4, 5, 6, 7, 8, 9]]
    >>> list(chunk(iter(range(10)),9))
    [[0, 1, 2, 3, 4, 5, 6, 7, 8], [9]]
    >>> list(chunk(iter(range(10)),5))
    [[0, 1, 2, 3, 4], [5, 6, 7, 8, 9]]
    >>> list(chunk(iter(range(10)),3))
    [[0, 1, 2], [3, 4, 5], [6, 7, 8], [9]]
    >>> list(chunk(iter(range(10)),1))
    [[0], [1], [2], [3], [4], [5], [6], [7], [8], [9]]
    """

    assert(slice > 0)
    a=[]

    for x in it:
        if len(a) >= slice :
            yield a
            a=[]
        a.append(x)

    if a:
        yield a


class ASNClient:
    def __init__(self, endpoint='tcp://localhost:5555'):
        context = zmq.Context()
        logger.debug("Connecting to asn lookup server")
        socket = context.socket(zmq.DEALER)
        socket.set(zmq.LINGER, 200)
        socket.connect(endpoint)
        self.socket = socket


        self.get_fields()

    def get_fields(self):
        self.socket.send_string("fields")
        if not self.socket.poll(timeout=3000):
            raise Timeout()

        self.fields = json.loads(self.socket.recv_string())
        logger.debug("fields=%s", self.fields)

    def lookup_many(self, ips):
        outstanding = 0

        for batch in chunk(ips, 100):
            msg = ' '.join(batch)
            self.socket.send_string(msg)
            outstanding += 1
            if outstanding < 10:
                continue
            if not self.socket.poll(timeout=3000):
                raise Timeout()
            response = self.socket.recv_string()
            outstanding -=1
            records = json.loads(response)
            for rec in records:
                yield dict(zip(self.fields, rec))

        for _ in range(outstanding):
            if not self.socket.poll(timeout=3000):
                raise Timeout()
            response = self.socket.recv_string()
            outstanding -=1
            records = json.loads(response)
            for rec in records:
                yield dict(zip(self.fields, rec))

    def lookup(self, ip):
        return next(self.lookup_many([ip]))


def main():
    logging.basicConfig(level=logging.INFO)

    endpoint = 'tcp://localhost:5555'
    if len(sys.argv) > 1:
        endpoint = sys.argv[1]
    c = ASNClient(endpoint)
    ips = (line.rstrip() for line in sys.stdin)
    for rec in c.lookup_many(ips):
        print("\t".join(str(rec[f]) for f in c.fields))

if __name__ == "__main__":
    main()