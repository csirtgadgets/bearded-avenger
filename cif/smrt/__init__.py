#!/usr/bin/env python

from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter
import logging
import textwrap
from cif.constants import LOG_FORMAT, DEFAULT_CONFIG, REMOTE
import os.path
from cif.client import Client
from cif.smrt.fetcher import Fetcher as HTTPFetcher
from cif.rule import Rule
from cif.observable import Observable
import cif.color
import pkgutil
import re


from pprint import pprint

PARSERS_PATH = os.path.join("cif", "smrt", "parser")
FETCHERS_PATH = os.path.join("cif", "smrt", "fetcher")
LIMIT = 10000000

import sys

# http://python-3-patterns-idioms-test.readthedocs.org/en/latest/Factory.html
# https://gist.github.com/pazdera/1099559


class Smrt(Client):

    def __init__(self, logger=logging.getLogger(__name__), **kwargs):
        super(Smrt, self).__init__(**kwargs)

        self.logger = logger

    def parse(self, rule, feed, data):
        if rule.parser:
            parser = rule.parser
        else:
            parser = 'pattern'

        for loader, modname, is_pkg in pkgutil.iter_modules([PARSERS_PATH]):
            self.logger.debug('testing: {0}'.format(modname))
            if modname == parser:
                self.logger.debug("using {0} to parse the data".format(modname))
                parser = loader.find_module(modname).load_module(modname)
                parser = parser.Plugin()
                data = parser.process(rule, feed, data)
                return data

        self.logger.debug(rule)
        raise RuntimeError

    def process(self, rule, feed=None, limit=None):
        handler = HTTPFetcher(feed, rule=rule)
        data = []

        if rule.fetcher:
            for loader, modname, is_pkg in pkgutil.iter_modules([FETCHERS_PATH]):
                self.logger.debug('testing: {0}'.format(modname))
                if modname == rule.fetcher:
                    self.logger.debug("using {0} to fetch the data".format(modname))
                    handler = loader.find_module(modname).load_module(modname)
                    handler = handler.Plugin(feed, rule=rule)

        data = handler.process()

        try:
            data = self.parse(rule, feed, data)
        except RuntimeError:
            self.logger.error("unable to parse data")
            raise

        if limit and len(data) > int(limit):
            data = data[0:int(limit)]

        self.logger.debug('submitting...')
        for idx, d in enumerate(data):
            self.submit(str(Observable(**d)))


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

    p.add_argument("-r", "--rule", dest="rule", help="specify the rules directory or specific rules file [default: %("
                   "default)s", default="rules/default")

    p.add_argument("-f", "--feed", dest="feed", help="specify the feed to process")

    p.add_argument("--remote", dest="remote", help="specify the remote api url [default: %(default)s", default=REMOTE)

    p.add_argument("--limit", dest="limit", help="limit the number of records processed [default: %(default)s",
                   default=LIMIT)
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
    rule = options['rule']

    s = Smrt(logger=logger, token=options.get('token'))

    if os.path.isdir(rule):
        for file in os.listdir(rule):
            if re.search("^\.\.?", file): # skip hidden files .file.swp, etc
                continue
            logger.debug("processing {0}/{1}".format(rule, file))
            r = Rule(path=os.path.join(rule, file))

            if not r.feeds:
                continue

            for feed in r.feeds:
                s.process(r, feed=feed, limit=options.get('limit'))
    else:
        logger.debug("processing {0}".format(rule))
        r = Rule(path=rule)

        if not r.feeds:
            logger.error("rules file contains no feeds")
            raise RuntimeError

        if options.get('feed'):
            s.process(r, feed=options['feed'], limit=options.get('limit'))
        else:
            for feed in r.feeds:
                s.process(r, feed=feed, limit=options.get('limit'))


    sys.exit()


if __name__ == "__main__":
    main()