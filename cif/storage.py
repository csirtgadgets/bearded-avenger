#!/usr/bin/env python

from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter
import logging
import textwrap
from cif.constants import LOG_FORMAT, DEFAULT_CONFIG, STORAGE_ADDR, CTRL_ADDR
import os.path
import pkgutil
import os
import time
import cif.generic
import zmq
from zmq.eventloop import ioloop
import ujson as json
from pprint import pprint

STORE_PATH = os.path.join("cif", "store")


class Storage(object):

    def __init__(self, logger=logging.getLogger(__name__), store='dummy', store_nodes=None, router=STORAGE_ADDR, **kwargs):
        self.logger = logger
        self.context = zmq.Context()
        self.router = self.context.socket(zmq.ROUTER)
        self.ctrl = self.context.socket(zmq.REQ)

        for loader, modname, is_pkg in pkgutil.iter_modules([STORE_PATH]):
            if modname == store:
                self.logger.info('Loading plugin: {0}'.format(modname))
                self.store = loader.find_module(modname).load_module(modname)
                self.store = self.store.Plugin()

        self.router = self.context.socket(zmq.ROUTER)
        self.logger.debug('connecting to router: {0}'.format(router))
        self.router.connect(STORAGE_ADDR)

        self.ctrl.connect(CTRL_ADDR)

        self.ctrl.send_multipart(['storage', 'ping', str(time.time())])
        id, mtype, data = self.ctrl.recv_multipart()
        if mtype == 'ack':
            self.logger.debug('storage online')

    def handle_message(self, s, e):
        self.logger.debug('message received')
        m = s.recv_multipart()

        self.logger.debug(m)
        id, mtype, token, data = m

        if isinstance(data, basestring):
            data = json.loads(data)

        handler = getattr(self, "handle_" + mtype)
        if handler == None:
            self.logger.error('message type {0} unknown'.format(mtype))
            self.router.send_multipart([id, '0'])
            return

        self.logger.debug("mtype: {0}".format(mtype))

        rv = handler(token, data)
        rv = json.dumps(rv)
        self.router.send_multipart([id, rv])

    def handle_search(self, token, data):
        self.logger.debug('searching')
        rv = self.store.search(data)
        return rv

    def handle_submission(self, token, data):
        self.logger.debug('submitting')

        try:
            x = self.store.submit(data)
        except Exception, err:
            self.logger.exception(err)
            return False

        self.logger.debug("success!")
        return x

    def run(self):
        loop = ioloop.IOLoop.instance()
        loop.add_handler(self.router, self.handle_message, zmq.POLLIN)
        loop.start()


def main():
    p = ArgumentParser(
        description=textwrap.dedent('''\
        example usage:
            $ cif-storage -d
        '''),
        formatter_class=RawDescriptionHelpFormatter,
        prog='cif-storage'
    )

    p.add_argument("-v", "--verbose", dest="verbose", action="count",help="set verbosity level [default: %(default)s]")
    p.add_argument("-d", "--debug", dest="debug", action="store_true", help="turn on the firehose")

    p.add_argument("--config", dest="config", help="specify a configuration file [default: %(default)s]",
                   default=os.path.join(os.path.expanduser("~"), DEFAULT_CONFIG))

    p.add_argument("--router", dest="router", help="specify the router backend [default: %(default)s]",
                   default=STORAGE_ADDR)

    p.add_argument("--store", dest="store", help="specify a store type [default: %(default)s", default="dummy")
    p.add_argument("--store-nodes", dest="store_nodes", help="specify store node addresses")

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

    s = Storage(router=options['router'], store=options['store'], store_nodes=options.get('store_nodes'))

    logger.info('running...')
    s.run()


if __name__ == "__main__":
    main()