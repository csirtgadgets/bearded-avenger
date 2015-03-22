from cif.smrt.parser import Parser
import re
from pprint import pprint
import sys

RE_COMMENTS = '^([#|;]+)'


class Pattern(Parser):

    def __init__(self, *args, **kwargs):
        super(Pattern, self).__init__(*args, **kwargs)

        self.comments = re.compile(RE_COMMENTS)

    def is_comment(self, line):
        if self.comments.match(line):
            return True
        return False

    def process(self, rule, feed, data, limit=10000000):
        cols = rule.defaults['values']

        max = 0
        rv = []
        for l in data:
            if self.is_comment(l):
                continue

            m = self.pattern.split(l)
            if len(cols):
                obs = rule.defaults
                for c in range(0, len(cols)):
                    if cols[c] is not None:
                        obs[cols[c]] = m[c]
                obs.pop("values", None)
                rv.append(obs)

            max += 1
            if max >= limit:
                break
        return rv