from urlparse import urlparse
import logging
import copy
from csirtg_indicator import Indicator


class Url(object):

    def __init__(self):

        self.logger = logging.getLogger(__name__)

    def process(self, i, router):
        if i.itype == 'url':
            u = urlparse(i.indicator)
            if u.netloc:
                fqdn = Indicator(**i.__dict__)
                fqdn.indicator = u.netloc
                fqdn.itype = 'fqdn'
                fqdn.confidence = (int(fqdn.confidence) / 2)
                fqdn.rdata = i.indicator

            self.logger.debug('sending to router..')
            x = router.indicators_create(fqdn)


Plugin = Url
