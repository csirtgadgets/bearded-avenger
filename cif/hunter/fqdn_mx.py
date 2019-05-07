import logging
from csirtg_indicator import resolve_itype
from csirtg_indicator.exceptions import InvalidIndicator
from cif.utils import resolve_ns
from csirtg_indicator import Indicator
from dns.resolver import Timeout
import re
from pprint import pprint
import arrow


class FqdnMx(object):

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.is_advanced = True

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

            if rr in ["", 'localhost', '0.0.0.0']:
                continue

            fqdn = Indicator(**i.__dict__())
            fqdn.indicator = rr.rstrip('.')
            fqdn.lasttime = arrow.utcnow()

            # 10
            if re.match('^\d+$', rr):
                return

            try:
                resolve_itype(fqdn.indicator)
            except InvalidIndicator as e:
                self.logger.info(fqdn)
                self.logger.info(e)
            else:
                fqdn.itype = 'fqdn'
                fqdn.rdata = i.indicator
                fqdn.confidence = (fqdn.confidence - 5) if fqdn.confidence >= 5 else 0
                router.indicators_create(fqdn)


Plugin = FqdnMx
