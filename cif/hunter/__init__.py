#!/usr/bin/env python

import json
import logging
import os
import sys
import textwrap
from argparse import ArgumentParser, RawDescriptionHelpFormatter

import zmq
from zmq.eventloop import ioloop

import cif.hunter
from cif.client.zeromq import ZMQ as Client
from cif.constants import HUNTER_ADDR, ROUTER_ADDR
from cif.indicator import Indicator
from cif.utils import setup_logging, get_argument_parser, setup_signals

TOKEN = os.getenv('CIF_HUNTER_TOKEN', 1234)


class Hunter(object):

    def handle_message(self, s, e):
        self.logger.info('handling message...')
        m = s.recv_multipart()
        m = json.loads(m[0])

        self.logger.debug(m)

        m = Indicator(**m)

        for p in self.plugins:
            p.process(m, self.router)

    def __init__(self, remote=HUNTER_ADDR, router=ROUTER_ADDR, token=TOKEN, loop=ioloop.IOLoop.instance(), *args,
                 **kvargs):

        self.logger = logging.getLogger(__name__)
        self.context = zmq.Context.instance()
        self.socket = self.context.socket(zmq.SUB)
        if sys.version_info > (3,):
            self.socket.setsockopt_string(zmq.SUBSCRIBE, '')
        else:
            self.socket.setsockopt(zmq.SUBSCRIBE, '')
        self.loop = loop
        self.loop.add_handler(self.socket, self.handle_message, zmq.POLLIN)

        self.plugins = []

        import pkgutil
        self.logger.debug('loading plugins...')
        for loader, modname, is_pkg in pkgutil.iter_modules(cif.hunter.__path__, 'cif.hunter.'):
            p = loader.find_module(modname).load_module(modname)
            self.plugins.append(p.Plugin(*args, **kvargs))
            self.logger.debug('plugin loaded: {}'.format(modname))

        self.hunters = remote

        self.router = Client(remote=router, token=token)

    def start(self):
        self.logger.debug('connecting to {}'.format(self.hunters))
        self.socket.connect(self.hunters)
        self.logger.debug('starting loop...')
        self.loop.start()
        self.logger.debug('started..')

    def stop(self):
        self.loop.stop()

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        return self


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
    p.add_argument('--router', help='cif-router front end address [default %(default)s]', default=ROUTER_ADDR)
    p.add_argument('--token', help='specify cif-hunter token [default %(default)s]', default=TOKEN)

    args = p.parse_args()
    setup_logging(args)

    logger = logging.getLogger(__name__)
    logger.info('loglevel is: {}'.format(logging.getLevelName(logger.getEffectiveLevel())))

    setup_signals(__name__)

    with Hunter(remote=args.remote, router=args.router, token=args.token) as h:
        try:
            logger.info('starting up...')
            h.start()
        except KeyboardInterrupt:
            logging.info("shutting down...")
            h.stop()

if __name__ == "__main__":
    main()