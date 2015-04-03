#!/usr/bin/env python

from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter
import logging
import textwrap
import requests
import time
import select
import sys
import os.path
import json

from pprint import pprint

from cif.constants import LOG_FORMAT, REMOTE, DEFAULT_CONFIG, ROUTER_FRONTEND
import cif.generic
import zmq
from cif.observable import Observable
from cif.format.table import Table

SNDTIMEO = 2000
RCVTIMEO = 30000
LINGER = 3


class Client(object):

    def __init__(self, remote=REMOTE, logger=logging.getLogger(__name__),
                 token=None, proxy=None, timeout=300, verify_ssl=True, **kwargs):
        self.logger = logger
        self.remote = remote
        self.token = str(token)
        self.proxy = proxy
        self.timeout = timeout
        self.verify_ssl = verify_ssl

        self.session = requests.Session()
        self.session.headers["Accept"] = 'application/vnd.cif.v3+json'
        self.session.headers['User-Agent'] = 'cif-sdk-python/0.0.0a'
        self.session.headers['Authorization'] = 'Token token=' + self.token
        self.session.headers['Content-Type'] = 'application/json'

    def get(self, uri, params={}):
        uri = self.remote + uri
        body = self.session.get(uri, params=params, verify=self.verify_ssl)

        if body.status_code > 303:
            err = 'request failed: %s' % str(body.status_code)
            self.logger.debug(err)
            try:
                err = json.loads(body.content).get('message')
            except ValueError as e:
                err = body.content

            self.logger.error(err)
            raise RuntimeWarning(err)

        self.logger.debug(body.content)
        body = json.loads(body.content)
        return body

    def post(self, uri, data):
        body = self.session.post(uri, data=data)

        if body.status_code > 303:
            err = 'request failed: %s' % str(body.status_code)
            self.logger.debug(err)
            err = body.content

            if body.status_code == 401:
                err = 'unauthroized'
                raise RuntimeError(err)
            elif body.status_code == 404:
                err = 'not found'
                raise RuntimeError(err)
            else:
                try:
                    err = json.loads(err).get('message')
                except ValueError as e:
                    err = body.content

                self.logger.error(err)
                raise RuntimeWarning(err)

        self.logger.debug(body.content)
        body = json.loads(body.content)
        return body

    def search(self):
        return []

    def submit(self, data):
        uri = "{0}/observables".format(self.remote)
        self.logger.debug(uri)
        rv = self.post(uri, data)
        return rv

    def ping(self, write=False):
        t0 = time.time()

        self.get('/ping')

        t1 = (time.time() - t0)
        self.logger.debug('return time: %.15f' % t1)
        return t1


class ZMQClient(object):
    def __init__(self, logger=logging.getLogger(__name__), remote=ROUTER_FRONTEND, token='1234', **kwargs):
        self.logger = logger
        self.remote = remote
        self.token = token

        self.context = zmq.Context.instance()
        self.socket = self.context.socket(zmq.REQ)
        self.socket.RCVTIMEO = RCVTIMEO
        self.socket.SNDTIMEO = SNDTIMEO
        self.socket.setsockopt(zmq.LINGER, LINGER)

    def send(self, mtype, data):

        if not isinstance(data, basestring):
            data = json.dumps(data)
        self.logger.debug('connecting to {0}'.format(self.remote))
        self.logger.debug("mtype {0}".format(mtype))
        self.socket.connect(self.remote)

        # zmq requires .encode
        self.socket.send_multipart([self.token.encode('utf-8'), mtype.encode('utf-8'), data.encode('utf-8')])
        return self.recv()

    def recv(self):
        mtype, data = self.socket.recv_multipart()
        data = json.loads(data)

        if data.get('status') == 'success':
            return data.get('data')
        else:
            self.logger.error(data.get('status'))
            self.logger.error(data.get('data'))
            raise RuntimeError

    def ping(self):
        self.send('ping', str(time.time()))
        return self.recv()

    def search(self, q, limit=100, filters={}):
        query = {
            "observable": q,
            "limit": limit
        }
        for k, v in filters:
            query[k] = v

        rv = self.send('search', data=query)
        return rv

    def submit(self, subject):
        o = Observable(subject)
        o = str(o)
        self.send('submission', data=o)
        rv = self.recv()
        rv = json.loads(rv)
        return rv


def main():
    p = ArgumentParser(
        description=textwrap.dedent('''\
        example usage:
            $ cif -q example.org -d
            $ cif --search 1.2.3.0/24
            $ cif --ping
        '''),
        formatter_class=RawDescriptionHelpFormatter,
        prog='cif'
    )

    p.add_argument("-v", "--verbose", dest="verbose", action="count",
                   help="set verbosity level [default: %(default)s]")
    p.add_argument('-d', '--debug', dest='debug', action="store_true")

    p.add_argument('--token', dest='token', help='specify api token')
    p.add_argument('-p', '--ping', dest='ping', action="store_true") #meg
    p.add_argument("--search", dest="search", help="search")
    p.add_argument("--submit", dest="submit", help="submit an observable")

    p.add_argument("--config", dest="config", help="specify a configuration file [default: %(default)s]",
                   default=os.path.join(os.path.expanduser("~"), DEFAULT_CONFIG))

    args = p.parse_args()

    loglevel = logging.WARNING
    if args.verbose:
        loglevel = logging.INFO
    if args.debug:
        loglevel = logging.DEBUG

    console = logging.StreamHandler()
    logging.getLogger('').setLevel(loglevel)
    console.setFormatter(logging.Formatter(LOG_FORMAT))
    logging.getLogger('').addHandler(console)
    logger = logging.getLogger(__name__)

    options = vars(args)

    if options.get('ping'):
        logger.info('running ping')
        for num in range(0,4):
            ret = ZMQClient().ping()
            if ret != 0:
                logger.info("roundtrip: %s ms" % ret)
                select.select([],[],[],1)
            else:
                logger.error('ping failed')
                raise RuntimeError
    elif options.get('search'):
        logger.info("searching for {0}".format(options.get("search")))
        rv = ZMQClient().search(options.get("search"))
        print Table(data=rv)
    elif options.get("submit"):
        logger.info("submitting {0}".format(options.get("submit")))
        rv = ZMQClient().submit(options.get("submit"))
        pprint(rv)

if __name__ == "__main__":
    main()