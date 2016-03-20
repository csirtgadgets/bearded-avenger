#!/usr/bin/env python

import logging
import textwrap
from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter

import json
import zmq
from zmq.eventloop import ioloop
import os
import sys
import cif.gatherer
from cif.client.zeromq import ZMQ as Client
from cif.constants import GATHER_ADDR, ROUTER_ADDR
from cif.indicator import Indicator
from cif.utils import setup_logging, get_argument_parser, setup_signals

TOKEN = os.getenv('CIF_GATHERER_TOKEN', 1234)



# http://martyalchin.com/2008/jan/10/simple-plugin-framework/
# http://wehart.blogspot.com/2009/01/python-plugin-frameworks.html
# http://yapsy.sourceforge.net/
# http://stackoverflow.com/questions/932069/building-a-minimal-plugin-architecture-in-python
# https://www.reddit.com/r/Python/comments/1qaepq/very_basic_plugin_system/
# http://stackoverflow.com/questions/4309607/whats-the-preferred-way-to-implement-a-hook-or-callback-in-python


class Gatherer(object):
    """
    Gatherers gather data about incoming indicators (geoip, asn, cc, etc...)
    """

    def handle_message(self, s, e):
        self.logger.info('handling message...')
        m = s.recv_multipart()
        m = json.loads(m[0])

        self.logger.debug(m)

        m = Indicator(**m)

        for p in self.plugins:
            p.process(m, self.router)

    def __init__(self, remote=GATHER_ADDR, router=ROUTER_ADDR, token=TOKEN, *args, **kv):

        self.logger = logging.getLogger(__name__)
        self.context = zmq.Context.instance()
        self.socket = self.context.socket(zmq.SUB)
        if sys.version_info > (3,):
            self.socket.setsockopt_string(zmq.SUBSCRIBE, '')
        else:
            self.socket.setsockopt(zmq.SUBSCRIBE, '')
        self.loop = ioloop.IOLoop.instance()
        self.loop.add_handler(self.socket, self.handle_message, zmq.POLLIN)

        self.plugins = []

        import pkgutil
        self.logger.debug('loading plugins...')
        for loader, modname, is_pkg in pkgutil.iter_modules(cif.gatherer.__path__, 'cif.gatherer.'):
            p = loader.find_module(modname).load_module(modname)
            self.plugins.append(p.Plugin(*args, **kv))
            self.logger.debug('plugin loaded: {}'.format(modname))

        self.gatherers = remote

        self.router = Client(remote=router, token=token)

    def start(self):
        self.logger.debug('connecting to {}'.format(self.gatherers))
        self.socket.connect(self.gatherers)
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
            $ cif-gatherer
        '''),
        formatter_class=RawDescriptionHelpFormatter,
        prog='cif-gatherer',
        parents=[p]
    )

    p.add_argument('--remote', help="cif-router gatherer address [default %(default)s]", default=GATHER_ADDR)
    p.add_argument('--router', help='cif-router front end address [default %(default)s]', default=ROUTER_ADDR)
    p.add_argument('--token', help='specify cif-gatherer token [default %(default)s]', default=TOKEN)

    args = p.parse_args()
    setup_logging(args)
    logger = logging.getLogger(__name__)
    logger.info('loglevel is: {}'.format(logging.getLevelName(logger.getEffectiveLevel())))

    setup_signals(__name__)

    with Gatherer(remote=args.remote, router=args.router, token=args.token) as r:
        logger.info('staring gatherer...')
        try:
            r.start()
        except KeyboardInterrupt:
            logger.info('shutting down...')

if __name__ == "__main__":
    main()