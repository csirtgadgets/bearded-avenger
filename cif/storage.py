#!/usr/bin/env python

from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter
import logging
import textwrap
from cif.constants import LOG_FORMAT, DEFAULT_CONFIG, ROUTER_BACKEND
import os.path
import cif.generic
import zmq
from zmq.eventloop import ioloop

from pprint import pprint


class Storage(object):

    def __init__(self, logger=logging.getLogger(__name__), **kwargs):
        self.logger = logger
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.ROUTER)

    def auth(self, *args, **kwargs):
        return True ##TODO

    def handle_message(self, s, e):
        self.logger.debug('message received')
        msg = s.recv_multipart()

        token = msg[0]
        mtype = msg[1]
        data = msg[2]

        try:
            handler = getattr(self, "handle_" + mtype)
        except AttributeError:
            self.logger.error('message type {0} unknown'.format(mtype))
            rv = 0
            self.socket.send(rv)
            return

        rv = handler(data)
        self.socket.send_json(rv)

    @auth
    def handle_search(self, token, data):
        self.logger.debug('searching')
        return []

    @auth
    def handle_submission(self, token, data):
        self.logger.debug('submitting')
        return []

    def run(self):
        loop = ioloop.IOLoop.instance()
        loop.add_handler(self.socket, self.handle_message, zmq.POLLIN)
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

    p.add_argument("--router", dest="router", help="specify the router backend [default: %(default)s",
                   default=ROUTER_BACKEND)

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

    s = Storage(router=options['router'])

    logger.info('running...')
    s.run()


if __name__ == "__main__":
    main()