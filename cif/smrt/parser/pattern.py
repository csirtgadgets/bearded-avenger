from cif.smrt.parser import Parser
import re
from pprint import pprint
import copy
import sys


class Pattern(Parser):

    def __init__(self, client, fetcher, rule, feed, limit=0):
        super(Pattern, self).__init__(client, fetcher, rule, feed, limit=0)

        self.pattern = self.rule.defaults.get('pattern')

        if self.rule.feeds[self.feed].get('pattern'):
            self.pattern = self.rule.feeds[self.feed].get('pattern')

        self.pattern = re.compile(self.pattern)
        self.limit = limit

    def process(self):
        cols = self.rule.defaults['values']

        limit = self.limit

        max = 0
        rv = []
        for l in self.fetcher.process():
            if self.is_comment(l):
                continue

            try:
                m = self.pattern.match(l).group()
            except ValueError:
                continue
            except AttributeError:
                continue

            if len(cols):
                obs = copy.deepcopy(self.rule.defaults)
                obs.pop("values", None)
                obs.pop("pattern", None)

                for idx, col in enumerate(cols):
                    if col is not None:
                        obs[col] = m[idx]


                r = self.client.submit(**obs)
                rv.append(r)

            max += 1
            if max >= limit:
                break

        return rv

Plugin = Pattern