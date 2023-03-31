import os
import logging
from csirtg_indicator import Indicator
from csirtg_indicator.utils import is_ipv4_net
from cif.utils import resolve_ns
import arrow
from ipaddress import ip_address

CONFIDENCE = 9
PROVIDER = 'spamhaus.org'
SPAMHAUS_DQS_KEY = os.environ.get('SPAMHAUS_DQS_KEY', None)

BASE_QUERY_URL = 'zen.spamhaus.org'
if SPAMHAUS_DQS_KEY and len(SPAMHAUS_DQS_KEY) == 26:
    BASE_QUERY_URL = '{}.zen.dq.spamhaus.net'.format(SPAMHAUS_DQS_KEY)

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
    '127.0.0.9': {
        'tags': 'hijacked',
        'description': 'Spamhaus DROP/EDROP Data',
    },
}


class SpamhausIp(object):

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.is_advanced = True
        self.mtypes_supported = { 'indicators_create' }
        self.itypes_supported = { 'ipv4', 'ipv6' }

    def _prereqs_met(self, i, **kwargs):
        if kwargs.get('mtype') not in self.mtypes_supported:
            return False

        if kwargs.get('nolog'):
            return False

        if i.itype not in self.itypes_supported or '/' in i.indicator:
            # don't support CIDRs even in ip itypes
            return False

        if i.provider == 'spamhaus.org' and not is_ipv4_net(i.indicator):
            return False

        return True

    def _preprocess_by_ipversion(self, indicator, itype):
        ip_str = str(indicator)
        # https://www.spamhaus.org/organization/statement/012/spamhaus-ipv6-blocklists-strategy-statement
        if itype == 'ipv6':
            data = ip_address(ip_str).exploded.replace(':', '')
            data = reversed(data)
        else:
            data = reversed(ip_str.split('.'))

        return data

    def _resolve(self, data):
        data = '{}.{}'.format('.'.join(data), BASE_QUERY_URL)
        data = resolve_ns(data)
        if data and data[0]:
            return data[0]

    def process(self, i, router, **kwargs):
        if not self._prereqs_met(i, **kwargs):
            return

        try:
            zen_lookup_str = self._preprocess_by_ipversion(i.indicator, i.itype)
            r = self._resolve(zen_lookup_str)

            try:
                r = CODES.get(str(r), None)
            except Exception as e:
                # https://www.spamhaus.org/faq/section/DNSBL%20Usage
                self.logger.error(e)
                self.logger.info('check spamhaus return codes')
                r = None

            if r:
                f = Indicator(**i.__dict__())

                f.tags = [r['tags']]
                if 'hunter' not in f.tags:
                    f.tags.append('hunter')
                f.description = r['description']
                f.confidence = CONFIDENCE
                f.provider = PROVIDER
                f.reference_tlp = 'clear'
                f.reference = 'http://www.spamhaus.org/query/bl?ip={}'.format(f.indicator)
                f.lasttime = f.reporttime = arrow.utcnow()
                x = router.indicators_create(f)
                self.logger.debug("Spamhaus IP: {}".format(x))

        except Exception as e:
            self.logger.error("[Hunter: SpamhausIp] {}: giving up on indicator {}".format(e, i))
            import traceback
            traceback.print_exc()


Plugin = SpamhausIp