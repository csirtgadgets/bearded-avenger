import logging
import re

RE_COMMENTS = '^([#|;]+)'


class Parser(object):

    def __init__(self, client, fetcher, rule, feed, limit=0, logger=logging.getLogger(__name__)):
        self.logger = logger
        self.client = client
        self.fetcher = fetcher
        self.rule = rule
        self.feed = feed
        self.limit = int(limit)

        self.comments = re.compile(RE_COMMENTS)

    def is_comment(self, line):
        if self.comments.match(line):
            return True
        return False

    def _defaults(self):
        defaults = self.rule.defaults

        if self.rule.feeds[self.feed].get('defaults'):
            for d in self.rule.feeds[self.feed].get('defaults'):
                defaults[d] = self.rule.feeds[self.feed]['defaults'][d]

        return defaults

    def process(self):
        raise NotImplementedError