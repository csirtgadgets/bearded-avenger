import logging
import subprocess
import os
from pprint import pprint

from cif.constants import VERSION, SMRT_CACHE

import magic
import re
RE_SUPPORTED_DECODE = re.compile("zip|lzf|lzma|xz|lzop")


class Fetcher(object):

    def __init__(self, rule, feed, cache=SMRT_CACHE):

        self.logger = logging.getLogger(__name__)
        self.feed = feed
        self.rule = rule
        self.cache = cache
        self.fetcher = rule.fetcher

        if self.rule.defaults.get('remote'):
            self.remote = self.rule.defaults.get('remote')
        else:
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

        if not self.fetcher:
            if self.remote.startswith('http'):
                self.fetcher = 'http'
            else:
                self.fetcher = 'file'

    def process(self, split="\n", limit=0):
        if self.fetcher == 'http':
            # using wget until we can find a better way to mirror files in python
            subprocess.check_call([
                'wget', '--header', self.ua,  '-q', self.remote, '-N', '-O', self.cache
            ])
        else:
            if self.fetcher == 'file':
                self.cache = self.remote
            else:
                raise NotImplementedError

        ftype = magic.from_file(self.cache, mime=True).decode('utf-8')
        self.logger.debug(ftype)

        if ftype.startswith('text'):
            with open(self.cache) as f:
                for l in f:
                    yield l.strip()

        # if ftype == "application/zip":
        #     with ZipFile(self.cache) as f:
        #         for m in f.infolist():
        #             while True:
        #                 yield f.read(m.filename).split(split)[0:limit]