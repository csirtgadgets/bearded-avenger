import logging
from csirtg_indicator import Indicator
import os


MIN_CONFIDENCE = os.environ.get('CIF_HUNTER_BGPWHITELIST_MIN_CONFIDENCE', 5)


class Ipv4ResolvePrefixWhitelist(object):

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def process(self, i, router):
        if i.itype not in ['ipv4', 'ipv6']:
            return

        if 'whitelist' not in i.tags:
            return

        if i.confidence < MIN_CONFIDENCE:
            return

        prefix = i.indicator.split('.')
        prefix = prefix[:3]
        prefix.append('0/24')
        prefix = '.'.join(prefix)

        ii = Indicator(**i.__dict__())

        ii.indicator = prefix
        ii.tags = ['whitelist']
        ii.confidence = (i.confidence - 2)
        x = router.indicators_create(ii)


Plugin = Ipv4ResolvePrefixWhitelist
