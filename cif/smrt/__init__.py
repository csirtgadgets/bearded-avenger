#!/usr/bin/env python

from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter
import logging
import textwrap
from cif.constants import LOG_FORMAT, DEFAULT_CONFIG, REMOTE
import os.path
from cif.client import Client
from cif.smrt.fetcher import Fetcher
from cif.rule import Rule
from cif.smrt.parser.pattern import Pattern
from cif.smrt.parser.delim import Pipe
from cif.observable import Observable
import cif.color

from pprint import pprint
import sys

# http://python-3-patterns-idioms-test.readthedocs.org/en/latest/Factory.html
# https://gist.github.com/pazdera/1099559


class Smrt(Client):

    def __init__(self, logger=logging.getLogger(__name__), **kwargs):
        super(Smrt, self).__init__(**kwargs)

        self.logger = logger

    def process(self, rule, feed=None, limit=None):
        rule = Rule(path=rule)

        self.logger.debug('fetching')
        data = Fetcher(feed, rule=rule).process()

        self.logger.debug('parsing')
        data = Pipe().process(rule, feed, data)

        for d in range(0, len(data)):
            x = Observable(**data[d])
            data.pop(d)
            data.insert(d, x)


        self.logger.debug('submitting')
        data = self.submit(data)


def main():
    p = ArgumentParser(
        description=textwrap.dedent('''\
        example usage:
            $ cif-smrt -v --rules /etc/cif/rules/default
            $ cif-smrt --rules /etc/cif/rules/default/drg.yml --feed ssh
        '''),
        formatter_class=RawDescriptionHelpFormatter,
        prog='cif-smrt'
    )

    p.add_argument("-v", "--verbose", dest="verbose", action="count",
                   help="set verbosity level [default: %(default)s]")
    p.add_argument('-d', '--debug', dest='debug', action="store_true")

    p.add_argument("--config", dest="config", help="specify a configuration file [default: %(default)s]",
                   default=os.path.join(os.path.expanduser("~"), DEFAULT_CONFIG))

    p.add_argument("-r", "--rules", dest="rules", help="specify the rules directory [default: %(default)s",
                   default="/etc/cif/rules/default")

    p.add_argument("-f", "--feed", dest="feed", help="specify the feed to process")

    p.add_argument("--remote", dest="remote", help="specify the remote api url [default: %(default)s", default=REMOTE)

    p.add_argument("--limit", dest="limit", help="limit the number of records processed")


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
    pprint(options)

    s = Smrt(logger=logger)

    s.process("rules/default/drg.yml", feed="ssh", limit=options.get('limit'))

if __name__ == "__main__":
    main()