from cif.smrt.parser import Parser
import re
from pprint import pprint
import sys

RE_COMMENTS = '^([#|;]+)'


class Pattern(Parser):

    def __init__(self, *args, **kwargs):
        super(Pattern, self).__init__(*args, **kwargs)

        self.comments = re.compile(RE_COMMENTS)
        self.pattern = None

    def is_comment(self, line):
        if self.comments.match(line):
            return True
        return False

    def process(self, rule, feed, data, limit=10000000):
        cols = rule.defaults['values']

        if self.pattern:
            pattern = self.pattern
        elif rule.defaults.get('pattern'):
            pattern = rule.defaults.get('pattern')
        elif rule.feeds[feed].get('pattern'):
            pattern = rule.feeds[feed].get('pattern')

        pattern = re.compile(pattern)

        max = 0
        rv = []
        for l in data:
            if self.is_comment(l):
                continue

            try:
                m = pattern.match(l).group()
            except ValueError:
                continue
            except AttributeError:
                continue

            if len(cols):
                obs = rule.defaults

                for idx, col in enumerate(cols):
                    if col is not None:
                        obs[col] = m[idx]
                obs.pop("values", None)
                obs.pop("pattern", None)
                rv.append(obs)

            max += 1
            if max >= limit:
                break
        return rv

Plugin = Pattern