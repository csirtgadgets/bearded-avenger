from cif.smrt.parser.pattern import Pattern
import re
from pprint import pprint


class Delim(Pattern):

    def __init__(self, *args, **kwargs):
        super(Delim, self).__init__(*args, **kwargs)

    def process(self):
        defaults = self.rule.defaults
        cols = defaults['values']

        if self.rule.feeds[self.feed].get('defaults'):
            for d in self.rule.feeds[self.feed].get('defaults'):
                defaults[d] = self.rule.feeds[self.feed]['defaults'][d]

        limit = int(self.limit)
        rv = []
        for l in self.fetcher.process():
            if l == '' or self.is_comment(l):
                continue

            m = self.pattern.split(l)
            if len(cols):
                obs = {}
                for k, v in defaults.iteritems():
                    obs[k] = v

                for idx, col in enumerate(cols):
                    if col is not None:
                        obs[col] = m[idx]
                obs.pop("values", None)
                pprint(obs)
                r = self.client.submit(**obs)
                rv.append(r)
            limit -= 1
            if limit == 0:
                break

        return rv

Plugin = Delim