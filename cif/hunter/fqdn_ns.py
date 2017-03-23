import logging
from csirtg_indicator import resolve_itype
from csirtg_indicator.exceptions import InvalidIndicator
from cif.utils import resolve_ns
from csirtg_indicator import Indicator
from dns.resolver import Timeout


class FqdnNs(object):

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.is_advanced = True

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
            if str(rr).rstrip('.') in ["", 'localhost']:
                continue

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
                ip.confidence = (ip.confidence - 4) if ip.confidence >= 4 else 0
                router.indicators_create(ip)

Plugin = FqdnNs
