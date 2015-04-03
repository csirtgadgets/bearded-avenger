import logging
import re


class Parser(object):

    def __init__(self, logger=logging.getLogger(__name__), **kwargs):
        self.logger = logger

    def understands(self, p):
        raise NotImplementedError()

    def process(self):
        raise NotImplementedError()