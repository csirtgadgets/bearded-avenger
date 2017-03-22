import logging
from csirtg_indicator import resolve_itype
from csirtg_indicator.exceptions import InvalidIndicator
from cif.utils import resolve_ns
from csirtg_indicator import Indicator
from dns.resolver import Timeout
import re
from pprint import pprint


class FqdnMx(object):

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def process(self, i, router):
        if i.itype != 'fqdn':
            return

        if 'search' in i.tags:
            return

        try:
            r = resolve_ns(i.indicator, t='MX')
        except Timeout:
            self.logger.info('timeout trying to resolve MX for: {}'.format(i.indicator))
            return

        for rr in r:
            rr = re.sub(r'^\d+ ', '', str(rr))
            rr = str(rr).rstrip('.')

            if rr in ["", 'localhost']:
                continue

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
                fqdn.confidence = (int(fqdn.confidence) - 5)
                router.indicators_create(fqdn)

Plugin = FqdnMx
