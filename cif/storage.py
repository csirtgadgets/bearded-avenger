#!/usr/bin/env python

from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter
import logging
import textwrap
from cif.constants import LOG_FORMAT, DEFAULT_CONFIG, ROUTER_BACKEND
import os.path
import cif.generic
import zmq

from pprint import pprint


class Storage(cif.generic.Generic):

    def __init__(self, router=ROUTER_BACKEND, **kwargs):
        super(Storage, self).__init__(socket=zmq.ROUTER, **kwargs)

        self.router = self.context.socket(zmq.DEALER)


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

    options = vars(args)
    pprint(options)
    s = Storage(router=options['router'])
    s.run()


if __name__ == "__main__":
    main()