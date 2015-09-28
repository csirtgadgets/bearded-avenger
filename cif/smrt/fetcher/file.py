import logging
import subprocess
import os.path
import os
from cif.smrt.fetcher import Fetcher, LIMIT
from pprint import pprint

from cif.constants import VERSION

import sys
import magic
import re
from zipfile import ZipFile
RE_SUPPORTED_DECODE = re.compile("zip|lzf|lzma|xz|lzop")

# move var/smrt to tempfile.gettempdir()

class File(Fetcher):

    def __init__(self, rule, feed, cache='var/smrt/', logger=logging.getLogger(__name__)):

        self.logger = logger
        self.feed = feed
        self.rule = rule
        self.cache = cache

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

    def process(self, split="\n", limit=LIMIT):
        ftype = magic.from_file(self.cache, mime=True)
        self.logger.debug(ftype)

        if ftype == 'text/plain':
            with open(self.cache) as f:
                while True:
                    yield f.readline().strip()

        # if ftype == "application/zip":
        #     with ZipFile(self.cache) as f:
        #         for m in f.infolist():
        #             while True:
        #                 yield f.read(m.filename).split(split)[0:limit]


Plugin = File