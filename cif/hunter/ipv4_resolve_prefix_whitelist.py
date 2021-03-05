import logging
from csirtg_indicator import Indicator, InvalidIndicator
import arrow
import ipaddress

class Ipv4ResolvePrefixWhitelist(object):

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.is_advanced = False

    def process(self, i, router):
        if i.itype != 'ipv4':
            return

        if 'whitelist' not in i.tags:
            return
        
        # only run this hunter if it's a single address (no CIDRs)
        if ipaddress.IPv4Network(i.indicator).prefixlen != 32:
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
