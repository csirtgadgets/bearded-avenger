import logging
from csirtg_indicator import Indicator, InvalidIndicator
import arrow


class Ipv4ResolvePrefixWhitelist(object):

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.is_advanced = False

    def process(self, i, router):
        if i.itype not in ['ipv4', 'ipv6']:
            return

        if 'whitelist' not in i.tags:
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

        ii.lasttime = arrow.utcnow()

        ii.indicator = prefix
        ii.tags = ['whitelist']
        ii.confidence = (ii.confidence - 2) if ii.confidence >= 2 else 0
        router.indicators_create(ii)


Plugin = Ipv4ResolvePrefixWhitelist
