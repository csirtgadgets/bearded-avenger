from cif.smrt.parser import Parser
import re
from pprint import pprint
import copy
import sys
import logging


class Pattern(Parser):

    def __init__(self, *args, **kwargs):
        super(Pattern, self).__init__(*args, **kwargs)

        self.pattern = self.rule.defaults.get('pattern')

        if self.rule.feeds[self.feed].get('pattern'):
            self.pattern = self.rule.feeds[self.feed].get('pattern')

        self.pattern = re.compile(self.pattern)

    def process(self):
        cols = self.rule.defaults['values']

        if isinstance(cols, basestring):
            cols = cols.split(',')

        rv = []
        for l in self.fetcher.process():
            self.logger.debug(l)
            if self.ignore(l):  # comment or skip
                continue
            try:
                m = self.pattern.search(l).groups()
                if isinstance(m, basestring):
                    m = [m]
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

                pprint(self.rule)
                r = self.client.submit(**obs)
                rv.append(r)

            if self.limit:
                self.limit -= 1

                if self.limit == 0:
                    self.logger.debug('limit reached...')
                    break

        return rv

Plugin = Pattern