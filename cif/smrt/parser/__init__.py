import logging
import re


class Parser(object):

    def __init__(self, client, fetcher, rule, feed=None, limit=None, logger=logging.getLogger(__name__)):
        self.logger = logger
        self.client = client
        self.fetcher = fetcher
        self.rule = rule
        self.feed = feed
        self.limit = limit

    def process(self):
        raise NotImplemented