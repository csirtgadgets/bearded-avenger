import logging
from cif.utils import resolve_ns
from csirtg_indicator import Indicator
from dns.resolver import Timeout
from csirtg_indicator import resolve_itype
from csirtg_indicator.exceptions import InvalidIndicator


class FqdnCname(object):

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def process(self, i, router):
        if i.itype != 'fqdn':
            return

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
                return

            fqdn.itype = 'fqdn'
            fqdn.confidence = (int(fqdn.confidence) / 2)
            router.indicators_create(fqdn)

Plugin = FqdnCname
