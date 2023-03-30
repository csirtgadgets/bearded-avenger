import logging
from csirtg_indicator import Indicator
from csirtg_indicator import resolve_itype
from csirtg_indicator.exceptions import InvalidIndicator
import arrow

class FqdnWl(object):

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.is_advanced = False
        self.mtypes_supported = { 'indicators_create' }
        self.itypes_supported = { 'fqdn' }

    def _prereqs_met(self, i, **kwargs):
        if kwargs.get('mtype') not in self.mtypes_supported:
            return False
            
        if i.itype not in self.itypes_supported:
            return False

        if 'whitelist' not in i.tags:
            return False

        return True

    def process(self, i, router, **kwargs):
        if not self._prereqs_met(i, **kwargs):
            return

        urls = []
        for p in ['http://', 'https://']:
            urls.append('{}{}'.format(p, i.indicator))
            if not i.indicator.startswith('www.'):
                urls.append('{}www.{}'.format(p, i.indicator))

        for u in urls:
            url = Indicator(**i.__dict__())
            url.indicator = u

            try:
                resolve_itype(url.indicator)
            except InvalidIndicator as e:
                self.logger.error(url)
                self.logger.error(e)
            else:
                url.tags = ['whitelist', 'hunter']
                url.itype = 'url'
                url.rdata = i.indicator
                url.lasttime = url.reporttime = arrow.utcnow()
                router.indicators_create(url)


Plugin = FqdnWl