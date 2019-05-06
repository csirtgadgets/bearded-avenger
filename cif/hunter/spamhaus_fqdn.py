
import logging
from csirtg_indicator import Indicator
from pprint import pprint
from cif.utils import resolve_ns
import arrow

CONFIDENCE = 9
PROVIDER = 'spamhaus.org'

CODES = {
    '127.0.1.2': {
        'tags': 'suspicious',
        'description': 'spammed domain',
    },
    '127.0.1.3': {
        'tags': 'suspicious',
        'description': 'spammed redirector / url shortener',
    },
    '127.0.1.4': {
        'tags': 'phishing',
        'description': 'phishing domain',
    },
    '127.0.1.5': {
        'tags': 'malware',
        'description': 'malware domain',
    },
    '127.0.1.6': {
        'tags': 'botnet',
        'description': 'Botnet C&C domain',
    },
    '127.0.1.102': {
        'tags': 'suspicious',
        'description': 'abused legit spam',
    },
    '127.0.1.103': {
        'tags': 'suspicious',
        'description': 'abused legit spammed redirector',
    },
    '127.0.1.104': {
        'tags': 'phishing',
        'description': 'abused legit phish',
    },
    '127.0.1.105': {
        'tags': 'malware',
        'description': 'abused legit malware',
    },
    '127.0.1.106': {
        'tags': 'botnet',
        'description': 'abused legit botnet',
    },
    '127.0.1.255': {
        'description': 'BANNED',
    },
}


class SpamhausFqdn(object):

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.is_advanced = True

    def _resolve(self, data):
        data = '{}.dbl.spamhaus.org'.format(data)
        data = resolve_ns(data)
        if data and data[0]:
            return data[0]

    def process(self, i, router):
        if 'search' in i.tags:
            return

        if i.itype == 'fqdn' and i.provider != 'spamhaus.org':
            try:
                r = self._resolve(i.indicator)
                try:
                    r = CODES.get(str(r), None)
                except Exception as e:
                    # https://www.spamhaus.org/faq/section/DNSBL%20Usage
                    self.logger.error(e)
                    self.logger.info('check spamhaus return codes')
                    r = None

                if r:
                    confidence = CONFIDENCE
                    if ' legit ' in r['description']:
                        confidence = 6

                    f = Indicator(**i.__dict__())

                    f.tags = [r['tags']]
                    f.description = r['description']
                    f.confidence = confidence
                    f.provider = PROVIDER
                    f.reference_tlp = 'white'
                    f.reference = 'http://www.spamhaus.org/query/dbl?domain={}'.format(f.indicator)
                    f.lasttime = arrow.utcnow()
                    x = router.indicators_create(f)
                    self.logger.debug(x)
            except KeyError as e:
                self.logger.error(e)


Plugin = SpamhausFqdn
