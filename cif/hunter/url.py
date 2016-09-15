from cifsdk.constants import PYVERSION
import logging
from csirtg_indicator import Indicator
import json

if PYVERSION > 2:
    from urllib.parse import urlparse
else:
    from urlparse import urlparse


class Url(object):

    def __init__(self):

        self.logger = logging.getLogger(__name__)

    def process(self, i, router):
        if i.itype == 'url':
            u = urlparse(i.indicator)
            if u.netloc:
                fqdn = Indicator(**i.__dict__())
                fqdn.indicator = u.netloc
                fqdn.itype = 'fqdn'
                fqdn.confidence = (int(fqdn.confidence) / 2)
                fqdn.rdata = i.indicator

            self.logger.debug('sending to router..')
            x = router.indicators_create(fqdn)


Plugin = Url
