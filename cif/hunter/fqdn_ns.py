import logging
from csirtg_indicator import resolve_itype
from csirtg_indicator.exceptions import InvalidIndicator
from cif.utils import resolve_ns
from cif.hunter import HUNTER_MIN_CONFIDENCE
from csirtg_indicator import Indicator
from dns.resolver import Timeout
import arrow


class FqdnNs(object):

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
            r = resolve_ns(i.indicator, t='NS')
        except Timeout:
            self.logger.info('timeout trying to resolve: {}'.format(i.indicator))
            return

        for rr in r:
            rr = str(rr).rstrip('.')
            if rr in ["", 'localhost', '0.0.0.0']:
                continue

            i_ns = Indicator(**i.__dict__())
            i_ns.indicator = rr

            try:
                i_ns_itype = resolve_itype(i_ns.indicator)
            except InvalidIndicator as e:
                self.logger.error(i_ns)
                self.logger.error(e)
            else:
                i_ns.lasttime = i_ns.reporttime = arrow.utcnow()
                i_ns.itype = i_ns_itype
                i_ns.rdata = "{} nameserver".format(i.indicator)
                if 'hunter' not in i_ns.tags:
                    i_ns.tags.append('hunter')
                # prevent hunters from running on insertion of this ns
                i_ns.confidence = max(0, min(i_ns.confidence, HUNTER_MIN_CONFIDENCE - 1))
                router.indicators_create(i_ns)
                self.logger.debug("FQDN NS Hunter: {}".format(i_ns))

Plugin = FqdnNs