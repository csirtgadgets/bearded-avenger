from cif.smrt.parser import Parser
import re
from pprint import pprint
import sys


class Pattern(Parser):

    def __init__(self, client, fetcher, rule, feed, limit=None):
        super(Pattern, self).__init__(client, fetcher, rule, feed, limit=None)

        if self.rule.defaults.get('pattern'):
            self.pattern = self.rule.defaults.get('pattern')
        elif self.rule.feeds[self.feed].get('pattern'):
            self.pattern = self.rule.feeds[self.feed].get('pattern')

        self.pattern = re.compile(self.pattern)

    def process(self):
        cols = self.rule.defaults['values']

        limit = self.limit
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
                obs = self.rule.defaults

                for idx, col in enumerate(cols):
                    if col is not None:
                        obs[col] = m[idx]
                obs.pop("values", None)
                obs.pop("pattern", None)
                r = self.client.submit(**obs)
                rv.append(r)

            max += 1
            if max >= limit:
                break

        return rv

Plugin = Pattern