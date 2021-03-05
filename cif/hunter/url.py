from cifsdk.constants import PYVERSION
import logging
from csirtg_indicator import Indicator, resolve_itype
from csirtg_indicator.exceptions import InvalidIndicator
import json
import arrow

if PYVERSION > 2:
    from urllib.parse import urlparse
else:
    from urlparse import urlparse


class Url(object):

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.is_advanced = False

    def process(self, i, router):
        if i.itype != 'url':
            return

        if 'search' in i.tags:
            return

        u = urlparse(i.indicator)
        if not u.hostname:
            return

        try:
            resolve_itype(u.hostname)
        except InvalidIndicator as e:
            self.logger.error(u.hostname)
            self.logger.error(e)
        else:
            fqdn = Indicator(**i.__dict__())
            fqdn.lasttime = fqdn.reporttime = arrow.utcnow()
            fqdn.indicator = u.hostname
            fqdn.itype = 'fqdn'
            if 'hunter' not in fqdn.tags:
                fqdn.tags.append('hunter')
            fqdn.confidence = (int(fqdn.confidence) / 2)
            fqdn.rdata = i.indicator

            self.logger.debug('[Hunter: Url] sending to router: {}'.format(fqdn))
            router.indicators_create(fqdn)


Plugin = Url
