from cif.smrt.parser import Parser
import re
from pprint import pprint
import sys

RE_COMMENTS = '^([#|;]+)'


class Pattern(Parser):

    def __init__(self, *args, **kwargs):
        super(Pattern, self).__init__(*args, **kwargs)

        self.comments = re.compile(RE_COMMENTS)

    def process(self, rule, feed, data, limit=10000000):

        max = 0
        for l in data:
            if not self.comments.match(l):
                print l

                max += 1
            if max >= limit:
                break

        return []
