import dns.resolver
import logging
from dns.name import EmptyLabel
from csirtg_indicator import Indicator
from pprint import pprint

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

    def __init__(self, *args, **kv):
        self.logger = logging.getLogger(__name__)

    def _resolve(self, data):
        data = '{}.dbl.spamhaus.org'.format(data)
        answers = dns.resolver.query(data, 'A')
        return answers[0]

    def process(self, i, router):
        if i.itype == 'fqdn' and i.provider != 'spamhaus.org':
            try:
                r = self._resolve(i.indicator)
                r = CODES[r]

                f = Indicator(**i.__dict__)

                f.tags = [r['tags']]
                f.description = r['description']
                f.confidence = CONFIDENCE
                f.provider = PROVIDER
                f.reference_tlp = 'white'
                f.reference = 'http://www.spamhaus.org/query/dbl?domain={}'.format(f.indicator)
                x = router.indicators_create(f)
                self.logger.debug(x)
            except KeyError as e:
                self.logger.error(e)
            except dns.resolver.NoAnswer:
                self.logger.info('no answer...')
            except dns.resolver.NXDOMAIN:
                self.logger.info('nxdomain...')
            except EmptyLabel:
                self.logger.error('empty label: {}'.format(i.indicator))


Plugin = SpamhausFqdn
