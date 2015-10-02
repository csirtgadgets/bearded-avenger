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

        self.skip = rule.defaults.get('skip', None)
        if self.skip:
            del rule.defaults['skip']
            self.skip = re.compile(self.skip)

    def ignore(self, line):
        if self.is_comment(line):
            return True

        if self.skip and self.skip.search(line):
            return True

    def is_comment(self, line):
        if self.comments.search(line):
            return True

    def _defaults(self):
        defaults = self.rule.defaults

        if self.rule.feeds[self.feed].get('defaults'):
            for d in self.rule.feeds[self.feed].get('defaults'):
                defaults[d] = self.rule.feeds[self.feed]['defaults'][d]

        return defaults

    def process(self):
        raise NotImplementedError