#!/usr/bin/env python

from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter
import logging
import textwrap
from cif.constants import CTRL_ADDR, FRONTEND_ADDR, STORAGE_ADDR, PUBLISH_ADDR

from pprint import pprint
import zmq
from zmq.eventloop import ioloop
import json
import time
from cif.utils import setup_logging, get_argument_parser


class Router(object):

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.stop()
        return self

    def __init__(self, frontend=FRONTEND_ADDR, publisher=PUBLISH_ADDR, storage=STORAGE_ADDR):
        self.logger = logging.getLogger(__name__)

        self.context = zmq.Context.instance()
        self.frontend = self.context.socket(zmq.ROUTER)
        self.storage = self.context.socket(zmq.DEALER)
        self.publisher = self.context.socket(zmq.PUB)
        self.ctrl = self.context.socket(zmq.REP)

        self.poller = zmq.Poller()

        self.ctrl.bind(CTRL_ADDR)
        self.frontend.bind(frontend)
        self.publisher.bind(publisher)
        self.storage.bind(storage)

    def auth(self, token):
        if not token:
            return 0
        return 1

    def handle_ctrl(self, s, e):
        self.logger.debug('ctrl msg recieved')
        id, mtype, data = s.recv_multipart()

        self.ctrl.send_multipart(['router', 'ack', str(time.time())])

    def handle_message(self, s, e):
        self.logger.debug('message received')
        m = s.recv_multipart()

        id, null, token, mtype, data = m
        self.logger.debug("mtype: {0}".format(mtype))

        if self.auth(token):
            handler = getattr(self, "handle_" + mtype)
            rv = handler(token, data)
        else:
            rv = json.dumps({
                "status": "failed",
                "data": "unauthorized"
            })

        self.logger.debug("replying {}".format(rv))
        self.frontend.send_multipart([id, '', mtype, rv])

    def handle_ping(self):
        rv = {
            "status": "success",
            "data": str(time.time())
        }
        return json.dumps(rv)

    def handle_write(self, data):
        rv = {
            "status": "failed",
            "data": str(time.time())
        }
        return json.dumps(rv)

    def handle_search(self, token, data):
        self.storage.send_multipart(['search', token, data])
        return self.storage.recv()

    def handle_submission(self, token, data):
        self.storage.send_multipart(['submission', token, data])
        m = self.storage.recv()
        return m

    def run(self):
        self.logger.debug('starting loop')
        loop = ioloop.IOLoop.instance()
        loop.add_handler(self.frontend, self.handle_message, zmq.POLLIN)
        loop.add_handler(self.ctrl, self.handle_ctrl, zmq.POLLIN)
        loop.start()

    def stop(self):
        return self


def main():
    p = get_argument_parser()
    p = ArgumentParser(
        description=textwrap.dedent('''\
        example usage:
            $ cif-router -d
        '''),
        formatter_class=RawDescriptionHelpFormatter,
        prog='cif-router',
        parents=[p]
    )

    p.add_argument('--frontend', help='address to listen on [default: %(default)s]', default=FRONTEND_ADDR)
    p.add_argument('--publish', help='address to publish on [default: %(default)s]', default=PUBLISH_ADDR)
    p.add_argument("--storage", help="specify a storage address [default: %(default)s]",
                   default=STORAGE_ADDR)

    args = p.parse_args()
    setup_logging(args)
    logger = logging.getLogger(__name__)

    with Router(frontend=args.frontend, publisher=args.publish, storage=args.storage) as r:
        try:
            logger.info('starting router..')
            r.run()
        except KeyboardInterrupt:
            logger.info('shutting down...')

if __name__ == "__main__":
    main()
