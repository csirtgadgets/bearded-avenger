import logging

from whiteface.feed import Feed

import re
from zipfile import ZipFile
RE_SUPPORTED_DECODE = re.compile("zip|lzf|lzma|xz|lzop")


class WhiteFace(object):

    def __init__(self, feed, cache='var/smrt/', rule=None, logger=logging.getLogger(__name__)):

        self.logger = logger
        self.feed = feed
        self.rule = rule
        self.cache = cache

        self.user, self.feed = self.feed.split("/")

    def process(self):
        feeds = Feed(user=self.user, feed=self.feed).index()
        import json
        return json.dumps([])

Plugin = WhiteFace