import dns.resolver
import logging
import dns.resolver
from dns.resolver import NXDOMAIN, NoAnswer
from pprint import pprint
from csirtg_indicator import Indicator

CONFIDENCE = 9
PROVIDER = 'spamhaus.org'

CODES = {
    '127.0.0.2': {
        'tags': 'spam',
        'description': 'Direct UBE sources, spam operations & spam services',
    },
    '127.0.0.3': {
        'tags': 'spam',
        'description': 'Direct snowshoe spam sources detected via automation',
    },
    '127.0.0.4': {
        'tags': 'exploit',
        'description': 'CBL + customised NJABL. 3rd party exploits (proxies, trojans, etc.)',
    },
    '127.0.0.5': {
        'tags': 'exploit',
        'description': 'CBL + customised NJABL. 3rd party exploits (proxies, trojans, etc.)',
    },
    '127.0.0.6': {
        'tags': 'exploit',
        'description': 'CBL + customised NJABL. 3rd party exploits (proxies, trojans, etc.)',
    },
    '127.0.0.7': {
        'tags': 'exploit',
        'description': 'CBL + customised NJABL. 3rd party exploits (proxies, trojans, etc.)',
    },
    '127.0.0.10': {
        'tags': 'spam',
        'description': 'End-user Non-MTA IP addresses set by ISP outbound mail policy',
    },
    '127.0.0.11': {
        'tags': 'spam',
        'description': 'End-user Non-MTA IP addresses set by ISP outbound mail policy',
    },
}


class SpamhausIp(object):

    def __init__(self, *args, **kv):
        self.logger = logging.getLogger(__name__)

    def _resolve(self, data):
        data = reversed(data.split('.'))
        data = '{}.zen.spamhaus.org'.format('.'.join(data))
        self.logger.debug(data)
        answers = dns.resolver.query(data, 'A')
        return answers[0]

    def process(self, i, router):
        if (i.itype == 'ipv4' or i.itype == 'ipv6') and i.provider != 'spamhaus.org':
            try:
                r = self._resolve(i.indicator)
                r = CODES.get(str(r), None)

                if r:
                    f = Indicator(**i.__dict__)

                    f.tags = [r['tags']]
                    f.description = r['description']
                    f.confidence = CONFIDENCE
                    f.provider = PROVIDER
                    f.reference_tlp = 'white'
                    f.reference = 'http://www.spamhaus.org/query/bl?ip={}'.format(f.indicator)
                    pprint(f)
                    x = router.indicator_create(f)
                    self.logger.debug(x)
            except NoAnswer:
                self.logger.info('no answer...')
            except NXDOMAIN:
                self.logger.info('nxdomain...')
            except Exception as e:
                self.logger.error(e)
                import traceback
                traceback.print_exc()


Plugin = SpamhausIp