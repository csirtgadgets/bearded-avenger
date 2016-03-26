from cif.smrt.parser import Parser
import re
from pprint import pprint
import copy
import sys
import logging
from cif.indicator import Indicator


class Pattern(Parser):

    def __init__(self, *args, **kwargs):
        super(Pattern, self).__init__(*args, **kwargs)

        self.pattern = self.rule.defaults.get('pattern')

        if self.rule.feeds[self.feed].get('pattern'):
            self.pattern = self.rule.feeds[self.feed].get('pattern')

        self.pattern = re.compile(self.pattern)

    def process(self):
        if self.rule.feeds[self.feed].get('values'):
            cols = self.rule.feeds[self.feed].get('values')
        else:
            cols = self.rule.defaults['values']
        defaults = self._defaults()

        if isinstance(cols, str):
            cols = cols.split(',')

        rv = []
        for l in self.fetcher.process():
            #self.logger.debug(l)

            if self.ignore(l):  # comment or skip
                continue

            try:
                m = self.pattern.search(l).groups()
                if isinstance(m, str):
                    m = [m]
            except ValueError:
                continue
            except AttributeError:
                continue

            if len(cols):
                i = copy.deepcopy(defaults)

                for idx, col in enumerate(cols):
                    if col is not None:
                        i[col] = m[idx]

                i.pop("values", None)
                i.pop("pattern", None)

                try:
                    i = Indicator(**i)
                except NotImplementedError as e:
                    self.logger.error(e)
                    self.logger.info('skipping: {}'.format(i['indicator']))
                else:
                    r = self.client.submit(i)
                    rv.append(r)

            if self.limit:
                self.limit -= 1

                if self.limit == 0:
                    self.logger.debug('limit reached...')
                    break

        return rv

Plugin = Pattern