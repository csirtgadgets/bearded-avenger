import os
import logging
from csirtg_indicator import Indicator
from cif.utils import resolve_ns
import arrow

CONFIDENCE = 9
PROVIDER = 'spamhaus.org'
SPAMHAUS_DQS_KEY = os.environ.get('SPAMHAUS_DQS_KEY', None)

BASE_QUERY_URL = 'dbl.spamhaus.org'
if SPAMHAUS_DQS_KEY and len(SPAMHAUS_DQS_KEY) == 26:
    BASE_QUERY_URL = '{}.dbl.dq.spamhaus.net'.format(SPAMHAUS_DQS_KEY)

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
        self.mtypes_supported = { 'indicators_create' }
        self.itypes_supported = { 'fqdn' }

    def _prereqs_met(self, i, **kwargs):
        if kwargs.get('mtype') not in self.mtypes_supported:
            return False
            
        if i.itype not in self.itypes_supported:
            return False

        if kwargs.get('nolog'):
            return False
            
        if i.provider == 'spamhaus.org':
            return False

        return True

    def _resolve(self, data):
        data = '{}.{}'.format(data, BASE_QUERY_URL)
        data = resolve_ns(data)
        if data and data[0]:
            return data[0]

    def process(self, i, router, **kwargs):
        if not self._prereqs_met(i, **kwargs):
            return

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
                if 'hunter' not in f.tags:
                    f.tags.append('hunter')
                f.description = r['description']
                f.confidence = confidence
                f.provider = PROVIDER
                f.reference_tlp = 'white'
                f.reference = 'http://www.spamhaus.org/query/dbl?domain={}'.format(f.indicator)
                f.lasttime = f.reporttime = arrow.utcnow()
                x = router.indicators_create(f)
                self.logger.debug("Spamhaus FQDN: {}".format(x))
        except KeyError as e:
            self.logger.error(e)
        except Exception as e:
            self.logger.error("[Hunter: SpamhausFqdn] {}: giving up on indicator {}".format(e, i))


Plugin = SpamhausFqdn