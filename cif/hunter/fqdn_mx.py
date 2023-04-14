import logging
from csirtg_indicator import resolve_itype
from csirtg_indicator.exceptions import InvalidIndicator
from cif.utils import resolve_ns
from cif.hunter import HUNTER_MIN_CONFIDENCE
from csirtg_indicator import Indicator
from dns.resolver import Timeout
import re
import arrow


class FqdnMx(object):

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.is_advanced = True
        self.mtypes_supported = { 'indicators_create' }
        self.itypes_supported = { 'fqdn' }

    def _prereqs_met(self, i, **kwargs):
        if kwargs.get('mtype') not in self.mtypes_supported:
            return False
            
        if i.itype not in self.itypes_supported:
            return False

        if 'search' in i.tags:
            return False

        return True

    def process(self, i, router, **kwargs):
        if not self._prereqs_met(i, **kwargs):
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
                elif re.match(r'^\d+$', rr) or re.match(r'^.{0,3}$', rr):
                    # exclude spurious entries like those too short to be real
                    continue

                mx = Indicator(**i.__dict__())
                mx.indicator = rr.rstrip('.')
                mx.lasttime = mx.reporttime = arrow.utcnow()

                try:
                    resolve_itype(mx.indicator)
                except InvalidIndicator as e:
                    self.logger.info(mx)
                    self.logger.info(e)
                else:
                    mx.itype = 'fqdn'
                    if 'hunter' not in mx.tags:
                        mx.tags.append('hunter')
                    mx.rdata = '{} mx'.format(i.indicator)
                    # prevent hunters from running on insertion of this mx
                    mx.confidence = max(0, min(mx.confidence, HUNTER_MIN_CONFIDENCE - 1))
                    router.indicators_create(mx)
                    self.logger.debug("FQDN MX Hunter: {}".format(mx))
                    
        except Exception as e:
            self.logger.error('[Hunter: FqdnMx] {}: giving up on rr {} from indicator {}'.format(e, rr, i))
                    
Plugin = FqdnMx