from cifsdk.constants import PYVERSION
import logging
from csirtg_indicator import Indicator, resolve_itype
from csirtg_indicator.exceptions import InvalidIndicator
import arrow

if PYVERSION > 2:
    from urllib.parse import urlparse
else:
    from urlparse import urlparse


class Url(object):

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.is_advanced = False
        self.mtypes_supported = { 'indicators_create' }
        self.itypes_supported = { 'url' }

    def _prereqs_met(self, i, **kwargs):
        if kwargs.get('mtype') not in self.mtypes_supported:
            return False

        if i.itype not in self.itypes_supported:
            return False

        if 'search' in i.tags:
            return False

        # prevent recursion with fqdn_wl hunter
        if ('whitelist') in i.tags and (i.rdata is not None or i.rdata != ''):
            return False

        return True

    def process(self, i, router, **kwargs):
        if not self._prereqs_met(i, **kwargs):
            return

        u = urlparse(i.indicator)
        if not u.hostname:
            return

        try:
            itype = resolve_itype(u.hostname)
        except InvalidIndicator as e:
            self.logger.error(u.hostname)
            self.logger.error(e)
        else:
            new_indicator = Indicator(**i.__dict__())
            new_indicator.lasttime = new_indicator.reporttime = arrow.utcnow()
            new_indicator.indicator = u.hostname
            new_indicator.itype = itype
            if 'hunter' not in new_indicator.tags:
                new_indicator.tags.append('hunter')

            if new_indicator.itype in [ 'ipv4', 'ipv6' ]:
                new_indicator.confidence = (new_indicator.confidence - 2) if new_indicator.confidence >= 2 else 0
            else:
                new_indicator.confidence = (int(new_indicator.confidence) / 2)
            new_indicator.rdata = i.indicator
            
            self.logger.debug('[Hunter: Url] sending to router {}'.format(new_indicator))
            router.indicators_create(new_indicator)


Plugin = Url