import time
import json
from cif.client import Client
from cif.exceptions import AuthError

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

        self.logger.debug('token: {}'.format(token))

    def _send(self, mtype, data='[]'):
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
        elif data.get('message') == 'unauthorized':
            raise AuthError('unauthorized')
        else:
            self.logger.error(data.get('status'))
            self.logger.error(data.get('data'))
            raise RuntimeError(data.get('message'))

    def test_connect(self):
        try:
            self.socket.RCVTIMEO = 5000
            self.ping()
            self.socket.RCVTIMEO = RCVTIMEO
        except zmq.error.Again:
            return False

        return True

    def ping(self, write=False):
        if write:
            return self._send('ping_write')
        else:
            return self._send('ping')

    def search(self, filters):
        rv = self._send('search', json.dumps(filters))
        return rv

    def submit(self, data):
        if isinstance(data, dict):
            data = self._kv_to_indicator(data)

        if not isinstance(data, str):
            data = str(data)

        sent = False
        tries = 5
        while tries > 0 and not sent:
            try:
                data = self._send("submission", data)
                sent = True
            except zmq.error.Again:
                self.logger.warning('timeout... retrying in 5s..')
                import time
                tries -= 1
                time.sleep(5)
        return data

    def tokens_search(self, filters={}):
        return self._send('tokens_search', json.dumps(filters))

    def tokens_create(self, data):
        return self._send('tokens_create', data)

    def tokens_delete(self, data):
        return self._send('tokens_delete', data)

    def token_edit(self, data):
        return self._send('token_edit', data)

Plugin = ZMQ
