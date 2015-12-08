#!/usr/bin/env python

from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter
import logging
import textwrap
from cif.constants import REMOTE_ADDR, SMRT_RULES_PATH, SMRT_CACHE
import os.path
from cif.rule import Rule
from cif.smrt.fetcher import Fetcher
from cif.utils import setup_logging, get_argument_parser, load_plugin, setup_signals
from random import randint
from time import sleep
import signal
from pprint import pprint
import cif.smrt.parser
import cif.client



PARSER_DEFAULT = "pattern"
TOKEN = os.environ.get('CIF_TOKEN', None)
TOKEN = os.environ.get('CIF_SMRT_TOKEN', TOKEN)


# http://python-3-patterns-idioms-test.readthedocs.org/en/latest/Factory.html
# https://gist.github.com/pazdera/1099559


class Smrt(object):
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def __enter__(self):
        return self

    def __init__(self, remote=REMOTE_ADDR, token=TOKEN, client='http'):

        self.logger = logging.getLogger(__name__)
        self.client = load_plugin(cif.client.__path__[0], client)(remote, token)

    def _process(self, rule, feed, limit=None):

        fetch = Fetcher(rule, feed)

        parser = rule.parser or PARSER_DEFAULT
        parser = load_plugin(cif.smrt.parser.__path__[0], parser)

        self.logger.debug("loading parser: {}".format(parser))

        parser = parser(self.client, fetch, rule, feed, limit=limit)

        rv = parser.process()

        return rv

    def process(self, rule, feed=None, limit=None):
        rv = []
        if isinstance(rule, basestring) and os.path.isdir(rule):
            for f in os.listdir(rule):
                if not f.startswith('.'):
                    self.logger.debug("processing {0}/{1}".format(rule, f))
                    r = Rule(path=os.path.join(rule, f))

                    if not r.feeds:
                        continue

                    for feed in r.feeds:
                        rv = self._process(r, feed, limit=limit)
        else:
            self.logger.debug("processing {0}".format(rule))
            r = rule
            if isinstance(rule, basestring):
                r = Rule(path=rule)

            if not r.feeds:
                self.logger.error("rules file contains no feeds")
                raise RuntimeError

            if feed:
                rv = self._process(r, feed=feed, limit=limit)
            else:
                for feed in r.feeds:
                    rv = self._process(Rule(path=rule), feed=feed, limit=limit)

        return rv


def main():
    p = get_argument_parser()
    p = ArgumentParser(
        description=textwrap.dedent('''\
        Env Variables:
            CIF_RUNTIME_PATH
            CIF_HTTP_ADDR
            CIF_TOKEN

        example usage:
            $ cif-smrt -v --rules rules/default
            $ cif-smrt --rules rules/default/drg.yml --feed ssh
        '''),
        formatter_class=RawDescriptionHelpFormatter,
        prog='cif-smrt',
        parents=[p],
    )

    p.add_argument("-r", "--rule", help="specify the rules directory or specific rules file [default: %(default)s",
                   default=SMRT_RULES_PATH)

    p.add_argument("-f", "--feed", help="specify the feed to process")

    p.add_argument("--remote", dest="remote", help="specify the remote api url [default: %(default)s",
                   default=REMOTE_ADDR)

    p.add_argument('--cache', help="specify feed cache [default %(default)s]", default=SMRT_CACHE)

    p.add_argument("--limit", dest="limit", help="limit the number of records processed [default: %(default)s]",
                   default=None)

    p.add_argument("--token", dest="token", help="specify token [default: %(default)s]", default=TOKEN)

    p.add_argument('--test', action='store_true')
    p.add_argument('--sleep', default=60)

    args = p.parse_args()

    setup_logging(args)
    logger = logging.getLogger(__name__)
    logger.info('loglevel is: {}'.format(logging.getLevelName(logger.getEffectiveLevel())))

    setup_signals(__name__)

    stop = False

    r = False
    if not args.test:
        r = randint(5, 55)
        logger.info("random delay is {}, then running every 60min after that".format(r))
        sleep((r * 60))

    while not stop:
        if args.test:
            stop = True

        logger.info('starting...')
        try:
            with Smrt(args.remote, args.token) as s:
                logger.info('staring up...')
                x = s.process(args.rule, feed=args.feed, limit=args.limit)
                logger.info('complete')

                if not args.test:
                    logger.info('sleeping for 1 hour')
                    sleep((60 * 60))
        except RuntimeError as e:
            logger.error(e)
            if str(e).startswith('submission failed'):
                stop = True
        except KeyboardInterrupt:
            logger.info('shutting down')
            stop = True

if __name__ == "__main__":
    main()