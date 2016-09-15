import logging
from cif.utils import resolve_ns
from csirtg_indicator import Indicator
from dns.resolver import Timeout
from pprint import pprint
from cifsdk.constants import PYVERSION
import re

def is_subdomain(i):
    bits = i.split('.')
    if len(bits) > 2:
        return True


class Fqdn(object):

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def process(self, i, router):
        if i.itype == 'fqdn':
            try:
                r = resolve_ns(i.indicator, t='CNAME')
            except Timeout:
                self.logger.info('timeout trying to resolve: {}'.format(i.indicator))
                r = []

            for rr in r:
                fqdn = Indicator(**i.__dict__())
                fqdn.indicator = str(rr).rstrip('.')
                fqdn.itype = 'fqdn'
                fqdn.confidence = (int(fqdn.confidence) / 2)
                x = router.indicators_create(fqdn)

            if i.is_subdomain():
                fqdn = Indicator(**i.__dict__())
                fqdn.indicator = i.is_subdomain()
                fqdn.confidence = (int(fqdn.confidence) / 3)
                x = router.indicators_create(fqdn)

            try:
                r = resolve_ns(i.indicator)
            except Timeout:
                self.logger.info('timeout trying to resolve: {}'.format(i.indicator))
                r = []

            for rr in r:
                ip = Indicator(**i.__dict__())
                ip.indicator = str(rr)
                ip.itype = 'ipv4'
                ip.rdata = i.indicator
                ip.confidence = (int(ip.confidence) / 4)
                x = router.indicators_create(ip)
                self.logger.debug(x)

            try:
                r = resolve_ns(i.indicator, t='NS')
            except Timeout:
                self.logger.info('timeout trying to resolve NS for: {}'.format(i.indicator))
                r = []

            for rr in r:
                ip = Indicator(**i.__dict__())
                ip.indicator = str(rr).rstrip('.')
                ip.itype = 'fqdn'
                ip.rdata = i.indicator
                ip.confidence = (int(ip.confidence) / 5)
                x = router.indicators_create(ip)
                self.logger.debug(x)

            try:
                r = resolve_ns(i.indicator, t='MX')
            except Timeout:
                self.logger.info('timeout trying to resolve MX for: {}'.format(i.indicator))
                r = []

            for rr in r:
                ip = Indicator(**i.__dict__())

                rr = re.sub(r'^\d{1,2} ', '', str(rr))
                ip.indicator = rr.rstrip('.')
                ip.itype = 'fqdn'
                ip.rdata = i.indicator
                ip.confidence = (int(ip.confidence) / 6)
                x = router.indicators_create(ip)
                self.logger.debug(x)


Plugin = Fqdn