#!/usr/bin/env python

from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter
import logging
import textwrap
import select
import os.path
from cif.format.table import Table
from pprint import pprint
from cif.observable import Observable
from cif.constants import LOG_FORMAT


class Client(object):

    def __init__(self, remote, token, logger=logging.getLogger(__name__)):
        self.logger = logger
        self.remote = remote
        self.token = str(token)

    def _kv_to_observable(self, kv):
        return str(Observable(**kv))


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

    p.add_argument('--token', dest='token', help='specify api token', default=str(1234))
    p.add_argument('-p', '--ping', dest='ping', action="store_true") #meg
    p.add_argument("--search", dest="search", help="search")
    p.add_argument("--submit", dest="submit", help="submit an observable")

    p.add_argument("--zmq", dest="zmq", help="use zmq as a transport instead of http", action="store_true")

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

    cli = Client(**options)
    if options.get("zmq"):
        from cif.client.zeromq import Client as ZMQClient
        cli = ZMQClient(**options)

    if options.get('ping'):
        logger.info('running ping')
        for num in range(0, 4):
            ret = cli.ping()
            if ret != 0:
                logger.info("roundtrip: %s ms" % ret)
                select.select([], [], [], 1)
            else:
                logger.error('ping failed')
                raise RuntimeError
    elif options.get('search'):
        logger.info("searching for {0}".format(options.get("search")))
        rv = cli.search(options.get("search"))
        print Table(data=rv)
    elif options.get("submit"):
        logger.info("submitting {0}".format(options.get("submit")))
        rv = cli.submit(options.get("submit"))
        pprint(rv)

if __name__ == "__main__":
    main()