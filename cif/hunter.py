#!/usr/bin/env python

import zmq
from zmq.eventloop import ioloop
from argparse import ArgumentParser, RawDescriptionHelpFormatter
import textwrap
import logging
import json
import sys
from cif.constants import HUNTER_ADDR
from cif.utils import setup_logging, get_argument_parser, setup_signals, load_plugin
from pprint import pprint
from cif.indicator import Indicator
import cif.hunter

class Hunter(object):

    def handle_message(s, e):
        m = s.recv_multipart()
        m = json.loads(m[0])
        m = Indicator(**m)
        print(m)

    def __init__(self, remote=HUNTER_ADDR, callback=handle_message, *args, **kv):

        self.logger = logging.getLogger(__name__)
        self.context = zmq.Context.instance()
        self.socket = self.context.socket(zmq.SUB)
        if sys.version_info > (3,):
            self.socket.setsockopt_string(zmq.SUBSCRIBE, '')
        else:
            self.socket.setsockopt(zmq.SUBSCRIBE, '')
        self.loop = ioloop.IOLoop.instance()
        self.loop.add_handler(self.socket, callback, zmq.POLLIN)

        self.plugins = []

        import pkgutil
        self.logger.debug('loading plugins...')
        for loader, modname, is_pkg in pkgutil.iter_modules(cif.hunter.__path__, 'cif.hunter.'):
            p = loader.find_module(modname).load_module(modname)
            self.plugin.append(p.Plugin(*args, **kv))
            self.logger.debug('plugin loaded: {}'.format(modname))

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