#!/usr/bin/env python

from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter
import logging
import textwrap
from cif.constants import LOG_FORMAT, DEFAULT_CONFIG
import cif.generic
import time
import os.path

from pprint import pprint
import zmq
import sys

ROUTER_LISTEN = 'tcp://0.0.0.0'
ROUTER_PUBLISH = 'tcp://0.0.0.0'


class Router(cif.generic.Generic):

    def __init__(self, listen='0.0.0.0', port=None, publisher_port=None, **kwargs):
        super(Router, self).__init__(socket=zmq.REP, **kwargs)

        self.socket.bind('tcp://{0}:{1}'.format(listen, port))
        # self.publisher.bind('tcp://{0}:{1}'.format(listen, publisher_port))

    def handle_message(self, s, e):
        self.logger.debug('message received')
        msg = s.recv_multipart()

        token = msg[0]
        mtype = msg[1]
        data = msg[2]

        if not self.auth(token):
            self.socket.send_json({
                "message": "failed",
                "data": "unauthorized"
            })
        else:
            try:
                handler = getattr(self, "handle_" + mtype)
            except AttributeError:
                self.logger.error('message type {0} unknown'.format(mtype))
                rv = 0
                self.socket.send(rv)
                return

            rv = handler(data)
            self.socket.send_json(rv)

    def auth(self, token):
        if not token:
            return 0
        return 1

    def handle_ping(self, msg):
        return str(time.time())

    def handle_write(self, msg):
        return str(time.time())

    def handle_search(self, msg):
        return [{
            "observable": msg
        }]

    def handle_submission(self, msg):
        pass

    def handle_auth(self, msg):
        pass

    def publish(self, msg):
        pass


def main():
    parser = ArgumentParser(
        description=textwrap.dedent('''\
        example usage:
            $ cif-router -d
        '''),
        formatter_class=RawDescriptionHelpFormatter,
        prog='cif-router'
    )

    parser.add_argument("-v", "--verbose", dest="verbose", action="count",
                        help="set verbosity level [default: %(default)s]")
    parser.add_argument('-d', '--debug', dest='debug', action="store_true")

    parser.add_argument('--listen', dest='listen', help='address to listen on', default=ROUTER_LISTEN)
    parser.add_argument('--listen-port', dest='listen_port', help='port to listen', default=ROUTER_PORT)

    parser.add_argument('--publish', dest='publish', help='address to publish on', default=ROUTER_PUBLISH)
    parser.add_argument('--publish-port', dest='publish_port', help='port to publish on', default=ROUTER_PUBLISHER_PORT)

    parser.add_argument("--storage", dest="storage", default="elasticsearch")
    parser.add_argument("--storage-host", dest="storage_host", default="127.0.0.0:9200")

    parser.add_argument("--config", dest="config", help="specify a configuration file [default: %(default)s]",
                        default=os.path.join(os.path.expanduser("~"), DEFAULT_CONFIG))


    args = parser.parse_args()

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
    pprint(options)

    r = Router(logger=logger)
    logger.info('staring router...')
    try:
        r.run()
    except KeyboardInterrupt:
        logger.info('shutting down...')
        sys.exit()



if __name__ == "__main__":
    main()