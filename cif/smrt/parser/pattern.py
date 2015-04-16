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

    def process(self, client, fetcher, rule, feed=None, limit=10000000):
        cols = rule.defaults['values']

        pattern = self.pattern

        if rule.defaults.get('pattern'):
            pattern = rule.defaults.get('pattern')
        elif rule.feeds[feed].get('pattern'):
            pattern = rule.feeds[feed].get('pattern')

        pattern = re.compile(pattern)

        for l in fetcher.process():
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
                pprint(obs)

            sys.exit()

            max += 1
            if max >= limit:
                break

Plugin = Pattern