#!/usr/bin/env python

import zmq
from zmq.eventloop import ioloop
from argparse import ArgumentParser, RawDescriptionHelpFormatter
import textwrap
import logging
import json

from cif.constants import HUNTER_ADDR
from cif.utils import setup_logging, get_argument_parser, setup_signals
from pprint import pprint
from cif.indicator import Indicator
from cif.format.table import Table


class Hunter(object):

    def handle_message(s, e):
        m = s.recv_multipart()
        m = json.loads(m[0])
        m = Indicator(**m)
        print(m)

    def __init__(self, remote=HUNTER_ADDR, callback=handle_message):

        self.logger = logging.getLogger(__name__)
        self.context = zmq.Context.instance()
        self.socket = self.context.socket(zmq.SUB)
        self.socket.setsockopt(zmq.SUBSCRIBE, '')
        self.loop = ioloop.IOLoop.instance()
        self.loop.add_handler(self.socket, callback, zmq.POLLIN)

        self.hunters = remote

    def start(self):
        self.logger.debug('connecting to {}'.format(self.hunters))
        self.socket.connect(self.hunters)
        self.logger.debug('starting loop...')
        self.loop.start()

    def stop(self):
        self.loop.stop()

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.stop()


def main():
    p = get_argument_parser()
    p = ArgumentParser(
        description=textwrap.dedent('''\
        example usage:
            $ cif-hunter -d
        '''),
        formatter_class=RawDescriptionHelpFormatter,
        prog='cif-hunter',
        parents=[p],
    )

    p.add_argument('--remote', help="cif-router hunter address [default %(default)s]", default=HUNTER_ADDR)

    args = p.parse_args()
    setup_logging(args)

    logger = logging.getLogger(__name__)
    logger.info('loglevel is: {}'.format(logging.getLevelName(logger.getEffectiveLevel())))

    setup_signals(__name__)

    with Hunter(remote=args.remote) as h:
        try:
            logger.info('starting up...')
            h.start()
        except KeyboardInterrupt:
            logging.info("shutting down...")

if __name__ == "__main__":
    main()