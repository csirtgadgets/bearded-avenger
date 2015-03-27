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
from cif.observable import Observable
import cif.color
import pkgutil

from pprint import pprint

PARSERS_PATH = os.path.join("cif", "smrt", "parser")

import sys

# http://python-3-patterns-idioms-test.readthedocs.org/en/latest/Factory.html
# https://gist.github.com/pazdera/1099559


class Smrt(Client):

    def __init__(self, logger=logging.getLogger(__name__), **kwargs):
        super(Smrt, self).__init__(**kwargs)

        self.logger = logger

    def parse(self, rule, feed, data):
        parser = rule.parser

        for loader, modname, is_pkg in pkgutil.iter_modules([PARSERS_PATH]):
            self.logger.debug('testing: {0}'.format(modname))
            if modname == parser:
                self.logger.debug("using {0} to parse the data".format(modname))
                parser = loader.find_module(modname).load_module(modname)
                parser = parser.Plugin()
                data = parser.process(rule, feed, data)
                return data

        raise RuntimeError

    def process(self, rule, feed=None, limit=None):
        rule = Rule(path=rule)

        self.logger.debug('fetching')
        data = Fetcher(feed, rule=rule).process()

        try:
            data = self.parse(rule, feed, data)
        except RuntimeError:
            self.logger.error("unable to parse data")
            raise

        data = [Observable(**item) for item in data]

        self.logger.debug('submitting')
        for d in range(0, (int(limit))):
            self.submit(str(data[d])) # since __repr__ jsonify's it for us


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
                   default="rules/default/drg.yml")

    p.add_argument("-f", "--feed", dest="feed", help="specify the feed to process")

    p.add_argument("--remote", dest="remote", help="specify the remote api url [default: %(default)s", default=REMOTE)

    p.add_argument("--limit", dest="limit", help="limit the number of records processed")
    p.add_argument("--token", dest="token", help="specify token")


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

    s = Smrt(logger=logger, token=options.get('token'))

    s.process(options.get('rules'), feed="ssh", limit=options.get('limit'))

if __name__ == "__main__":
    main()