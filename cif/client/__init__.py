#!/usr/bin/env python

import logging
import os.path
import select
import textwrap
from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter

from cif.constants import REMOTE_ADDR, SEARCH_LIMIT, CONFIG_PATH
from cif.format.table import Table
from cif.indicator import Indicator
from cif.utils import setup_logging, get_argument_parser, read_config
from cif.exceptions import AuthError

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

    p.add_argument('--token', help='specify api token', default=TOKEN)
    p.add_argument('--remote', help='specify API remote [default %(default)s]', default=REMOTE_ADDR)
    p.add_argument('-p', '--ping', action="store_true") # meg?
    p.add_argument('-q', '--search', help="search")
    p.add_argument('--itype', help='filter by indicator type')  ## need to fix sqlite for non-ascii stuff first
    p.add_argument("--submit", action="store_true", help="submit an indicator")
    p.add_argument('--limit', help='limit results [default %(default)s]', default=SEARCH_LIMIT)
    p.add_argument('--nolog', help='do not log search', action='store_true')

    p.add_argument('--indicator')
    p.add_argument('--tags', nargs='+')

    p.add_argument("--zmq", help="use zmq as a transport instead of http", action="store_true")

    p.add_argument('--config', help='specify config file [default %(default)s]', default=CONFIG_PATH)

    args = p.parse_args()

    setup_logging(args)
    logger = logging.getLogger(__name__)

    o = read_config(args)
    options = vars(args)
    for v in options:
        if options[v] is None:
            options[v] = o.get(v)

    if not options.get('token'):
        raise RuntimeError('missing --token')

    verify_ssl = True
    if o.get('no_verify_ssl') or options.get('no_verify_ssl'):
        verify_ssl = False

    options = vars(args)

    if options.get("zmq"):
        from cif.client.zeromq import ZMQ as ZMQClient
        cli = ZMQClient(**options)
    else:
        from cif.client.http import HTTP as HTTPClient
        cli = HTTPClient(args.remote, args.token, verify_ssl=verify_ssl)

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
    elif options.get('itype'):
        logger.info('searching for {}'.format(options['itype']))
        try:
            rv = cli.search({
                'itype': options['itype'],
                'limit': options['limit'],
            })
        except AuthError as e:
            logger.error('unauthorized')
        except RuntimeError as e:
            import traceback
            traceback.print_exc()
            logger.error(e)
        else:
            print(Table(data=rv))
    elif options.get('search'):
        logger.info("searching for {0}".format(options.get("search")))
        try:
            rv = cli.search({
                    'indicator': options['search'],
                    'limit': options['limit'],
                    'nolog': options['nolog']
                }
            )
        except RuntimeError as e:
            import traceback
            traceback.print_exc()
            logger.error(e)
        except AuthError as e:
            logger.error('unauthorized')
        else:
            print(Table(data=rv))
    elif options.get("submit"):
        logger.info("submitting {0}".format(options.get("submit")))

        rv = cli.submit(indicator=args.indicator, tags=args.tags)

if __name__ == "__main__":
    main()