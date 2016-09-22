import logging
from cif.utils import resolve_ns
from csirtg_indicator import Indicator
from dns.resolver import Timeout
from pprint import pprint
from cifsdk.constants import PYVERSION
from csirtg_indicator import resolve_itype
from csirtg_indicator.exceptions import InvalidIndicator
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
                try:
                    resolve_itype(fqdn.indicator)
                except InvalidIndicator as e:
                    self.logger.error(fqdn)
                    self.logger.error(e)
                else:
                    fqdn.itype = 'fqdn'
                    fqdn.confidence = (int(fqdn.confidence) / 2)
                    router.indicators_create(fqdn)

            if i.is_subdomain():
                fqdn = Indicator(**i.__dict__())
                fqdn.indicator = i.is_subdomain()
                try:
                    resolve_itype(fqdn.indicator)
                except InvalidIndicator as e:
                    self.logger.error(fqdn)
                    self.logger.error(e)
                else:
                    fqdn.confidence = (int(fqdn.confidence) / 3)
                    router.indicators_create(fqdn)

            try:
                r = resolve_ns(i.indicator)
            except Timeout:
                self.logger.info('timeout trying to resolve: {}'.format(i.indicator))
                r = []

            for rr in r:
                ip = Indicator(**i.__dict__())
                ip.indicator = str(rr)
                try:
                    resolve_itype(ip.indicator)
                except InvalidIndicator as e:
                    self.logger.error(ip)
                    self.logger.error(e)
                else:
                    ip.itype = 'ipv4'
                    ip.rdata = i.indicator
                    ip.confidence = (int(ip.confidence) / 4)
                    router.indicators_create(ip)

            try:
                r = resolve_ns(i.indicator, t='NS')
            except Timeout:
                self.logger.info('timeout trying to resolve NS for: {}'.format(i.indicator))
                r = []

            for rr in r:
                fqdn = Indicator(**i.__dict__())
                fqdn.indicator = str(rr).rstrip('.')
                try:
                    resolve_itype(fqdn.indicator)
                except InvalidIndicator as e:
                    self.logger.error(fqdn)
                    self.logger.error(e)
                else:
                    fqdn.itype = 'fqdn'
                    fqdn.rdata = i.indicator
                    fqdn.confidence = (int(fqdn.confidence) / 5)
                    router.indicators_create(fqdn)

            try:
                r = resolve_ns(i.indicator, t='MX')
            except Timeout:
                self.logger.info('timeout trying to resolve MX for: {}'.format(i.indicator))
                r = []

            for rr in r:
                rr = re.sub(r'^\d+ ', '', str(rr))
                fqdn = Indicator(**i.__dict__())
                fqdn.indicator = rr.rstrip('.')
                try:
                    resolve_itype(fqdn.indicator)
                except InvalidIndicator as e:
                    self.logger.error(fqdn)
                    self.logger.error(e)
                else:
                    fqdn.itype = 'fqdn'
                    fqdn.rdata = i.indicator
                    fqdn.confidence = (int(fqdn.confidence) / 6)
                    router.indicators_create(fqdn)


Plugin = Fqdn