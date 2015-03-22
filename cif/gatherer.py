#!/usr/bin/env python

from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter
import logging
import textwrap
import cif.generic
from cif.constants import ROUTER_PUBLISHER, DEFAULT_CONFIG, ROUTER_FRONTEND, ROUTER_GATHERER, LOG_FORMAT
import os.path
import sys
import zmq


class Gatherer(cif.generic.Generic):
    """
    Gatherers gather data about incoming observables (geoip, asn, cc, etc...)
    """

    def __init__(self, **kwargs):
        super(Gatherer, self).__init__(socket=zmq.SUB, **kwargs)

        # self.router = self.context.socket(zmq.REQ)
        # self.workers = self.context.socket(zmq.PUSH)

    def handle_message(self, s, e):
        pass


def main():
    p = ArgumentParser(
        description=textwrap.dedent('''\
        example usage:
            $ cif-gatherer
        '''),
        formatter_class=RawDescriptionHelpFormatter,
        prog='cif-gatherer'
    )

    p.add_argument("-v", "--verbose", dest="verbose", action="count",
                        help="set verbosity level [default: %(default)s]")
    p.add_argument('-d', '--debug', dest='debug', action="store_true")

    p.add_argument("--config", dest="config", help="specify a configuration file [default: %(default)s]",
                   default=os.path.join(os.path.expanduser("~"), DEFAULT_CONFIG))

    p.add_argument("--remote", dest="remote", help="specify the cif-router publishing channel [default: %(default)s",
                   default=ROUTER_GATHERER)


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

    r = Gatherer(logger=logger)
    logger.info('staring gatherer...')
    try:
        r.run()
    except KeyboardInterrupt:
        logger.info('shutting down...')
        sys.exit()
if __name__ == "__main__":
    main()