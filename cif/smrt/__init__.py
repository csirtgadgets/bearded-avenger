#!/usr/bin/env python

from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter
import logging
import textwrap
from cif.constants import REMOTE_ADDR
import os.path
from cif.rule import Rule
from cif.smrt.fetcher import Fetcher
from cif.utils import setup_logging, get_argument_parser, load_plugin


from pprint import pprint

PARSERS_PATH = os.path.join("cif", "smrt", "parser")
FETCHERS_PATH = os.path.join("cif", "smrt", "fetcher")
CLIENTS_PATH = os.path.join("cif", "client")

PARSER_DEFAULT = "pattern"
TOKEN = os.environ.get('CIF_TOKEN', None)
TOKEN = os.environ.get('CIF_SMRT_TOKEN', TOKEN)


# http://python-3-patterns-idioms-test.readthedocs.org/en/latest/Factory.html
# https://gist.github.com/pazdera/1099559


class Smrt(object):

    def __init__(self, remote, token):

        self.logger = logging.getLogger(__name__)
        self.client = load_plugin(CLIENTS_PATH, 'http')(remote, token)

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
    p = get_argument_parser()
    p = ArgumentParser(
        description=textwrap.dedent('''\
        example usage:
            $ cif-smrt -v --rules rules/default
            $ cif-smrt --rules rules/default/drg.yml --feed ssh
        '''),
        formatter_class=RawDescriptionHelpFormatter,
        prog='cif-smrt',
        parents=[p],
    )

    p.add_argument("-r", "--rule", dest="rule", help="specify the rules directory or specific rules file [default: %("
                   "default)s", default="rules/default")

    p.add_argument("-f", "--feed", dest="feed", help="specify the feed to process")

    p.add_argument("--remote", dest="remote", help="specify the remote api url [default: %(default)s",
                   default=REMOTE_ADDR)

    p.add_argument("--limit", dest="limit", help="limit the number of records processed [default: %(default)s]",
                   default=0)

    p.add_argument("--token", dest="token", help="specify token [default: %(default)s]", default=TOKEN)

    args = p.parse_args()

    setup_logging(args)
    logger = logging.getLogger(__name__)

    with Smrt(args.remote, args.token) as s:
        try:
            logger.info('staring up...')
            x = s.process(args.rule, feed=args.feed, limit=args.limit)
        except KeyboardInterrupt:
            logging.error("shutting down...")

if __name__ == "__main__":
    main()