import feedparser
from cif.smrt.parser import Parser
from cif.indicator import Indicator
import copy
import re


class Rss(Parser):

    def __init__(self, *args, **kwargs):
        super(Rss, self).__init__(*args, **kwargs)

    def process(self):
        defaults = self._defaults()

        patterns = copy.deepcopy(self.rule.feeds[self.feed]['pattern'])
        for p in patterns:
            patterns[p]['pattern'] = re.compile(patterns[p]['pattern'])

        feed = []
        for l in self.fetcher.process():
            feed.append(l)

        feed = "\n".join(feed)
        try:
            feed = feedparser.parse(feed)
        except Exception as e:
            self.logger.error('Error parsing feed: {}'.format(e))
            self.logger.error(defaults['remote'])
            raise e

        rv = []
        for e in feed.entries:
            i = copy.deepcopy(defaults)

            for k in e:
                if k == 'summary' and patterns.get('description'):
                    try:
                        m = patterns['description']['pattern'].search(e[k]).groups()
                    except AttributeError:
                        continue
                    for idx, c in enumerate(patterns['description']['values']):
                        i[c] = m[idx]
                elif patterns.get(k):
                    try:
                        m = patterns[k]['pattern'].search(e[k]).groups()
                    except AttributeError:
                        continue
                    for idx, c in enumerate(patterns[k]['values']):
                        i[c] = m[idx]

            if not i.get('indicator'):
                self.logger.error('missing indicator: {}'.format(e[k]))
                continue

            try:
                from cif.utils import normalize_itype
                from pprint import pprint
                i = normalize_itype(i)
                i = Indicator(**i)
                self.logger.debug(i)
            except NotImplementedError as e:
                self.logger.error(e)
                self.logger.info('skipping: {}'.format(i['indicator']))
            else:
                r = self.client.submit(i)
                rv.append(r)
        return rv

Plugin = Rss