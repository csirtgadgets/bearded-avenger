import logging
from csirtg_indicator import resolve_itype
from csirtg_indicator.exceptions import InvalidIndicator
from cif.utils import resolve_ns
from csirtg_indicator import Indicator
from dns.resolver import Timeout
import re
import arrow


class FqdnMx(object):

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.is_advanced = True

    def process(self, i, router, **kwargs):
        if i.itype != 'fqdn':
            return

        if 'search' in i.tags:
            return

        try:
            r = resolve_ns(i.indicator, t='MX')
        except Timeout:
            self.logger.info('timeout trying to resolve MX for: {}'.format(i.indicator))
            return

        try:
            for rr in r:
                rr = re.sub(r'^\d+ ', '', str(rr))
                rr = str(rr).rstrip('.')

                if rr in ["", 'localhost', '0.0.0.0']:
                    continue
                elif re.match('^\d+$', rr) or re.match(r'^.{0,3}$', rr):
                    # exclude spurious entries like those too short to be real
                    continue

                fqdn = Indicator(**i.__dict__())
                fqdn.indicator = rr.rstrip('.')
                fqdn.lasttime = fqdn.reporttime = arrow.utcnow()

                try:
                    resolve_itype(fqdn.indicator)
                except InvalidIndicator as e:
                    self.logger.info(fqdn)
                    self.logger.info(e)
                else:
                    fqdn.itype = 'fqdn'
                    if 'hunter' not in fqdn.tags:
                        fqdn.tags.append('hunter')
                    fqdn.rdata = '{} mx'.format(i.indicator)
                    fqdn.confidence = (fqdn.confidence - 5) if fqdn.confidence >= 5 else 0
                    router.indicators_create(fqdn)
                    self.logger.debug("FQDN MX Hunter: {}".format(fqdn))
        
        except Exception as e:
            self.logger.error('[Hunter: FqdnMx] {}: giving up on rr {} from indicator {}'.format(e, rr, i))

Plugin = FqdnMx
