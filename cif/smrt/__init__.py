#!/usr/bin/env python

from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter
import logging
import textwrap
from cif.constants import LOG_FORMAT, DEFAULT_CONFIG, REMOTE
import os.path
from cif.rule import Rule
import cif.color
from cif.utils import load_plugin
from cif.smrt.fetcher import Fetcher
import re


from pprint import pprint

PARSERS_PATH = os.path.join("cif", "smrt", "parser")
FETCHERS_PATH = os.path.join("cif", "smrt", "fetcher")
CLIENTS_PATH = os.path.join("cif", "client")
CLIENT_DEFAULT = "http"
FETCHER_DEFAULT = "http"
PARSER_DEFAULT = "pattern"
LIMIT = os.environ.get('CIF_SMRT_LIMIT', 10000)
TOKEN = os.environ.get('CIF_TOKEN', None)
REMOTE = os.environ.get('CIF_REMOTE', 'http://localhost:5000')

import sys

# http://python-3-patterns-idioms-test.readthedocs.org/en/latest/Factory.html
# https://gist.github.com/pazdera/1099559


class Smrt(object):

    def __init__(self, remote, token, client=CLIENT_DEFAULT, logger=logging.getLogger(__name__)):

        self.logger = logger
        self.client = load_plugin(CLIENTS_PATH, client)(remote, token)

    def _process(self, rule, feed, limit=0):

        fetch = Fetcher(rule, feed)

        parser = rule.parser or PARSER_DEFAULT
        parser = load_plugin(PARSERS_PATH, parser)

        parser = parser(self.client, fetch, rule, feed, limit=limit)

        rv = parser.process()

        return rv

    def process(self, rule, feed=None, limit=0):
        rv = []
        if type(rule) == str and os.path.isdir(rule):
            for f in os.listdir(rule):
                if not f.startswith('.'):
                    self.logger.debug("processing {0}/{1}".format(rule, file))
                    r = Rule(path=os.path.join(rule, file))

                    if not r.feeds:
                        continue

                    for feed in r.feeds:
                        rv = self._process(r, feed, limit=limit)
        else:
            self.logger.debug("processing {0}".format(rule))
            if type(rule) == str:
                rule = Rule(path=rule)

            if not rule.feeds:
                self.logger.error("rules file contains no feeds")
                raise RuntimeError

            if feed:
                rv = self._process(rule, feed=feed, limit=limit)
            else:
                for feed in r.feeds:
                    rv = self._process(rule, feed=feed, limit=limit)

        return rv


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
    p.add_argument("--token", dest="token", help="specify token", default="1234")

    p.add_argument("--client", dest="client", help="specify a client transport [http|zeromq, default %(default)s",
                   default=CLIENT_DEFAULT)

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

    s = Smrt(options["remote"], options["token"], options["client"], logger=logger)

    try:
        x = s.process(rule, feed=options.get("feed"), limit=options.get("limit"))
        pprint(x)
    except KeyboardInterrupt:
        sys.exit()


if __name__ == "__main__":
    main()