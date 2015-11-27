#!/usr/bin/env python

from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter
import logging
import textwrap
import select
import os.path
from cif.format.table import Table
from pprint import pprint
from cif.indicator import Indicator
from cif.constants import REMOTE_ADDR
from cif.utils import setup_logging, get_argument_parser

TOKEN = os.environ.get('CIF_TOKEN', None)
REMOTE_ADDR = os.environ.get('CIF_REMOTE', REMOTE_ADDR)


class Client(object):

    def __init__(self, remote, token):
        self.logger = logging.getLogger(__name__)
        self.remote = remote
        self.token = str(token)

    def _kv_to_indicator(self, kv):
        return Indicator(**kv)

    def ping(self):
        raise NotImplementedError

    def search(self):
        raise NotImplementedError


def main():
    p = get_argument_parser()
    p = ArgumentParser(
        description=textwrap.dedent('''\
        example usage:
            $ cif -q example.org -d
            $ cif --search 1.2.3.0/24
            $ cif --ping
        '''),
        formatter_class=RawDescriptionHelpFormatter,
        prog='cif',
        parents=[p]
    )

    p.add_argument('--token', help='specify api token', default=str(1234))
    p.add_argument('--remote', help='specify API remote [default %(default)s]', default=REMOTE_ADDR)
    p.add_argument('-p', '--ping', action="store_true") # meg?
    p.add_argument('-q', '--search', help="search")
    p.add_argument("--submit", action="store_true", help="submit an indicator")

    p.add_argument('--indicator')
    p.add_argument('--tags', nargs='+')

    p.add_argument("--zmq", dest="zmq", help="use zmq as a transport instead of http", action="store_true")

    args = p.parse_args()

    setup_logging(args)
    logger = logging.getLogger(__name__)

    options = vars(args)

    if options.get("zmq"):
        from cif.client.zeromq import ZMQ as ZMQClient
        cli = ZMQClient(**options)
    else:
        from cif.client.http import HTTP as HTTPClient
        cli = HTTPClient(args.remote, args.token)

    if options.get('ping'):
        logger.info('running ping')
        for num in range(0, 4):
            ret = cli.ping()
            if ret != 0:
                print("roundtrip: {} ms".format(ret))
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

        rv = cli.submit(indicator=args.indicator, tags=args.tags)

if __name__ == "__main__":
    main()