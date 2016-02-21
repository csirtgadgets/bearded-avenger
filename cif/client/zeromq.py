import time
import json
from cif.client import Client

from pprint import pprint

import zmq

SNDTIMEO = 2000
RCVTIMEO = 30000
LINGER = 3
ENCODING_DEFAULT = "utf-8"
SEARCH_LIMIT = 100


class ZMQ(Client):
    def __init__(self, remote, token):
        super(ZMQ, self).__init__(remote, token)

        self.context = zmq.Context.instance()
        self.socket = self.context.socket(zmq.REQ)
        self.socket.RCVTIMEO = RCVTIMEO
        self.socket.SNDTIMEO = SNDTIMEO
        self.socket.setsockopt(zmq.LINGER, LINGER)

    def _send(self, mtype, data):
        self.logger.debug('connecting to {0}'.format(self.remote))
        self.logger.debug("mtype {0}".format(mtype))
        self.socket.connect(self.remote)

        # zmq requires .encode
        self.logger.debug("sending")
        self.socket.send_multipart([self.token.encode(ENCODING_DEFAULT),
                                    mtype.encode(ENCODING_DEFAULT),
                                    data.encode(ENCODING_DEFAULT)])
        self.logger.debug("receiving")
        return self._recv()

    def _recv(self):
        mtype, data = self.socket.recv_multipart()
        data = json.loads(data)

        if data.get('status') == 'success':
            return data.get('data')
        else:
            self.logger.error(data.get('status'))
            self.logger.error(data.get('data'))
            raise RuntimeError(data.get('status'))

    def ping(self):
        return self._send('ping', str(time.time()))

    def search(self, filters):
        rv = self._send('search', json.dumps(filters))
        return rv

    def submit(self, data):
        if isinstance(data, dict):
            data = self._kv_to_indicator(data)

        data = self._send("submission", data)
        return data

Plugin = ZMQ
