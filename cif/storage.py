#!/usr/bin/env python

from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter
import logging
import textwrap
from cif.constants import CTRL_ADDR, STORAGE_ADDR
import pkgutil
import os
import time
import zmq
from zmq.eventloop import ioloop
import ujson as json
from pprint import pprint
from cif.errors import CIFConnectionError, StorageSubmissionFailed
import inspect
from cif.utils import setup_logging, get_argument_parser

MOD_PATH = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))

STORE_PATH = os.path.join(MOD_PATH, "store")
RCVTIMEO = 5000
SNDTIMEO = 2000
LINGER = 3
STORE_DEFAULT = 'dummy'
STORE_PLUGINS = ['dummy', 'sqlite', 'elasticsearch', 'rdflib']


class Storage(object):
    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.stop()

    def __init__(self, store=STORE_DEFAULT, router=STORAGE_ADDR, *args, **kv):
        self.logger = logging.getLogger(__name__)
        self.context = zmq.Context()
        self.router = self.context.socket(zmq.ROUTER)
        self.router_addr = router
        self.connected = False
        self.ctrl = None
        self.loop = ioloop.IOLoop.instance()

        for loader, modname, is_pkg in pkgutil.iter_modules([STORE_PATH]):
            if modname == store:
                self.logger.debug('Loading plugin: {0}'.format(modname))
                self.store = loader.find_module(modname).load_module(modname)
                self.store = self.store.Plugin(*args, **kv)

        self.router = self.context.socket(zmq.ROUTER)

    def start(self):
        while not self.connected:
            try:
                self.logger.debug('connecting to router: {0}'.format(self.router))
                self._connect_ctrl()
            except zmq.error.Again:
                self.logger.error("problem connecting to router, retrying...")
            except CIFConnectionError:
                self.logger.error("unable to connect")
                raise
            except KeyboardInterrupt:
                raise SystemExit
            else:
                self.connected = True

        self.router.connect(STORAGE_ADDR)

        self.loop.add_handler(self.router, self.handle_message, zmq.POLLIN)
        self.loop.start()

    def stop(self):
        self.loop.stop()

    def _connect_ctrl(self):
        if self.ctrl:
            self.connected = False
            self.ctrl.close()
            self.ctrl = None

        self.ctrl = self.context.socket(zmq.REQ)
        self.ctrl.RCVTIMEO = RCVTIMEO
        self.ctrl.SNDTIMEO = SNDTIMEO
        self.ctrl.setsockopt(zmq.LINGER, LINGER)

        self.ctrl.connect(CTRL_ADDR)
        self.ctrl.send_multipart(['storage', 'ping', str(time.time())])
        id, mtype, data = self.ctrl.recv_multipart()
        if mtype != 'ack':
            raise CIFConnectionError("connection rejected by router: {}".format(mtype))

    def handle_message(self, s, e):
        self.logger.debug('message received')
        m = s.recv_multipart()

        id, mtype, token, data = m

        if isinstance(data, basestring):
            try:
                data = json.loads(data)
            except ValueError as e:
                self.logger.error(e)
                self.router.send_multipart(["", json.dumps({"status": "failed" })])

        handler = getattr(self, "handle_" + mtype)
        if handler:
            self.logger.debug("mtype: {0}".format(mtype))

            self.logger.debug('running handler: {}'.format(mtype))

            try:
                rv = handler(token, data)
                rv = {"status": "success", "data": rv}
            except Exception as e:
                self.logger.error(e)
                rv = {"status": "failed"}

            rv = json.dumps(rv)
            self.router.send_multipart([id, rv])
        else:
            self.logger.error('message type {0} unknown'.format(mtype))
            self.router.send_multipart([id, '0'])

    def handle_search(self, token, data):
        self.logger.debug('searching')
        return self.store.search(data)

    def handle_submission(self, token, data):
        return self.store.submit(data)


def main():
    p = get_argument_parser()
    p = ArgumentParser(
        description=textwrap.dedent('''\
        example usage:
            $ cif-storage -d
        '''),
        formatter_class=RawDescriptionHelpFormatter,
        prog='cif-storage',
        parents=[p]
    )

    p.add_argument("--router", help="specify the storage address [default: %(default)s]",
                   default=STORAGE_ADDR)

    p.add_argument("--store", help="specify a store type {} [default: %(default)s]".format(', '.join(STORE_PLUGINS)),
                   default=STORE_DEFAULT)

    args = p.parse_args()

    setup_logging(args)
    logger = logging.getLogger(__name__)

    with Storage(router=args.router, store=args.store) as s:
        try:
            logger.info('starting up...')
            s.start()
        except KeyboardInterrupt:
            logger.info('shutting down...')

if __name__ == "__main__":
    main()
