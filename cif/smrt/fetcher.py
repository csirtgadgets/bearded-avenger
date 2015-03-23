import logging
import subprocess
import os.path
import os
from pprint import pprint

from cif.constants import VERSION
LIMIT = 10000000000
import sys


class Fetcher(object):

    def __init__(self, feed, cache='var/smrt/', rule=None, logger=logging.getLogger(__name__)):

        self.logger = logger
        self.feed = feed
        self.rule = rule
        self.cache = cache
        self.remote = self.rule.feeds[feed]['remote']

        self.dir = os.path.join(self.cache, self.rule.defaults.get('provider'))

        if not os.path.exists(self.dir):
            try:
                os.makedirs(self.dir)
            except OSError:
                self.logger.critical('failed to create {0}'.format(self.dir))
                raise

        self.cache = os.path.join(self.dir, self.feed)

        self.logger.debug(self.cache)

        # http://www-archive.mozilla.org/build/revised-user-agent-strings.html
        self.ua = "User-Agent: cif-smrt/{0} (csirtgadgets.org)".format(VERSION)

    def process(self, split="\n", limit=LIMIT):

        # using wget until we can find a better way to mirror files in python
        subprocess.check_call(['wget', '--header', self.ua, '--quiet', '-c', self.remote, '-O', self.cache])

        with open(self.cache) as f:
            content = f.read().split(split)[0:limit]

        f.close()
        return content