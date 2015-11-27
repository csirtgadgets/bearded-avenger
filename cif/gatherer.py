#!/usr/bin/env python

from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter
import logging
import textwrap
import cif.generic
from cif.constants import GATHER_ADDR
import zmq
from cif.utils import setup_logging, get_argument_parser


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

    with Gatherer() as r:
        logger.info('staring gatherer...')
        try:
            r.run()
        except KeyboardInterrupt:
            logger.info('shutting down...')

if __name__ == "__main__":
    main()