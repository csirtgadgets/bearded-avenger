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
        if i.itype != 'fqdn':
            return

        if 'search' in i.tags:
            return

        try:
            r = resolve_ns(i.indicator)
        except Timeout:
            self.logger.info('timeout trying to resolve: {}'.format(i.indicator))
            return

        for rr in r:
            rr = str(rr)
            if rr in ["", 'localhost']:
                continue

            ip = Indicator(**i.__dict__())
            ip.indicator = rr
            try:
                resolve_itype(ip.indicator)
            except InvalidIndicator as e:
                self.logger.error(ip)
                self.logger.error(e)
            else:
                ip.itype = 'ipv4'
                ip.rdata = i.indicator
                ip.confidence = (ip.confidence - 2) if ip.confidence >= 2 else 0
                router.indicators_create(ip)

                # also create a passive dns tag
                ip.tags = 'pdns'
                ip.confidence = 10
                router.indicators_create(ip)

Plugin = Fqdn