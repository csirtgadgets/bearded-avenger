#!/usr/bin/env python

from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter
import logging
import textwrap
import cif.generic
from cif.constants import GATHER_ADDR
import zmq
from cif.utils import setup_logging, get_argument_parser, setup_signals


# http://martyalchin.com/2008/jan/10/simple-plugin-framework/
# http://wehart.blogspot.com/2009/01/python-plugin-frameworks.html
# http://yapsy.sourceforge.net/
# http://stackoverflow.com/questions/932069/building-a-minimal-plugin-architecture-in-python
# https://www.reddit.com/r/Python/comments/1qaepq/very_basic_plugin_system/
# http://stackoverflow.com/questions/4309607/whats-the-preferred-way-to-implement-a-hook-or-callback-in-python


class Gatherer(cif.generic.Generic):
    """
    Gatherers gather data about incoming indicators (geoip, asn, cc, etc...)
    """

    def __init__(self, **kwargs):
        super(Gatherer, self).__init__(socket=zmq.SUB, **kwargs)

        # self.router = self.context.socket(zmq.REQ)
        # self.workers = self.context.socket(zmq.PUSH)

    def handle_message(self, s, e):
        pass


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

    p.add_argument("--remote", dest="remote", help="specify the cif-router publishing channel [default: %(default)s",
                   default=GATHER_ADDR)

    args = p.parse_args()
    logger = setup_logging(args)
    logger.info('loglevel is: {}'.format(logging.getLevelName(logger.getEffectiveLevel())))

    setup_signals(__name__)

    with Gatherer() as r:
        logger.info('staring gatherer...')
        try:
            r.run()
        except KeyboardInterrupt:
            logger.info('shutting down...')

if __name__ == "__main__":
    main()