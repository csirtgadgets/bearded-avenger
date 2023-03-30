import logging
from csirtg_indicator import Indicator, InvalidIndicator
import arrow
import ipaddress

class Ipv4ResolvePrefixWhitelist(object):

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.is_advanced = False
        self.mtypes_supported = { 'indicators_create' }
        self.itypes_supported = { 'ipv4' }

    def _prereqs_met(self, i, **kwargs):
        if kwargs.get('mtype') not in self.mtypes_supported:
            return False
            
        if i.itype not in self.itypes_supported:
            return False

        if 'whitelist' not in i.tags:
            return False
        
        # only run this hunter if it's a single address (no CIDRs)
        if ipaddress.IPv4Network(i.indicator).prefixlen != 32:
            return False

        return True

    def process(self, i, router, **kwargs):
        if not self._prereqs_met(i, **kwargs):
            return

        prefix = i.indicator.split('.')
        prefix = prefix[:3]
        prefix.append('0/24')
        prefix = '.'.join(prefix)

        try:
            ii = Indicator(**i.__dict__())
        except InvalidIndicator as e:
            self.logger.error(e)
            return

        ii.lasttime = ii.reporttime = arrow.utcnow()

        ii.indicator = prefix
        ii.tags = ['whitelist', 'hunter']
        ii.confidence = (ii.confidence - 2) if ii.confidence >= 2 else 0
        router.indicators_create(ii)


Plugin = Ipv4ResolvePrefixWhitelist