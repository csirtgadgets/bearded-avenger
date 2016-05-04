#!/usr/bin/env python

import logging
import os.path
import select
import textwrap
from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter

from cif.constants import REMOTE_ADDR, SEARCH_LIMIT
from cif.utils import setup_logging, get_argument_parser
from pprint import pprint

TOKEN = os.environ.get('CIF_TOKEN', None)
REMOTE_ADDR = os.environ.get('CIF_REMOTE', REMOTE_ADDR)


def main():
    p = get_argument_parser()
    p = ArgumentParser(
        description=textwrap.dedent('''\
        example usage:
            $ cif-tokens --name wes@csirtgadgets.org --create --admin
        '''),
        formatter_class=RawDescriptionHelpFormatter,
        prog='cif',
        parents=[p]
    )

    p.add_argument('--token', help='specify api token', default=str(1234))
    p.add_argument('--remote', help='specify API remote [default %(default)s]', default=REMOTE_ADDR)

    p.add_argument('--create', help='create token (requires admin token', action='store_true')
    p.add_argument('--delete', help='delete token (requires admin token)', action='store_true')

    p.add_argument('--username', help='specify username')
    p.add_argument('--admin', action='store_true')
    p.add_argument('--expires', help='set a token expiration timestamp')
    p.add_argument('--read', help='set the token read flag', action='store_true')
    p.add_argument('--write', help='set the token write flag', action='store_true')
    p.add_argument('--revoked', help='set the token revoked flag', action='store_true')
    p.add_argument('--groups', help='specify token groups (eg: everyone,group1,group2)')
    p.add_argument('--no-everyone', help="do not create key in the 'everyone' group", action='store_true')
    p.add_argument('--acl', help='set the token itype acls (eg: ipv4,ipv6)')

    args = p.parse_args()

    setup_logging(args)
    logger = logging.getLogger(__name__)

    options = vars(args)

    from cif.client.http import HTTP as HTTPClient
    cli = HTTPClient(args.remote, args.token)

    if options.get('create'):
        groups = set(options.get('groups').split(','))
        if not options.get('no_everyone'):
            if 'everyone' not in groups:
                groups.add('everyone')

        acl = options.get('acl').split(',')

        try:
            rv = cli.tokens_create({
                'username': options.get('username'),
                'admin': options.get('admin'),
                'expires': options.get('expires'),
                'read': options.get('revoked'),
                'write': options.get('write'),
                'groups': list(groups),
                'acl': acl
            })
        except Exception as e:
            logger.error('token create failed: {}'.format(e))
        else:
            pprint(rv)
    elif options.get('delete'):
        try:
            rv = cli.tokens_delete(options.get('token'))
        except Exception as e:
            logger.error('token delete failed: %s' % e)
        else:
            pprint(rv)
    else:
        try:
            rv = cli.tokens_search({
                'username': options.get('username'),
            })
        except Exception as e:
            logger.error('token search failed: {}'.format(e))
        else:
            pprint(rv)

if __name__ == "__main__":
    main()