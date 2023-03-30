import logging
from csirtg_indicator import Indicator
from csirtg_indicator import resolve_itype
from csirtg_indicator.exceptions import InvalidIndicator
import arrow


class FqdnSubdomain(object):

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

        if 'search' in i.tags:
            return False

        if not i.is_subdomain():
            return False

        return True

    def process(self, i, router, **kwargs):
        if not self._prereqs_met(i, **kwargs):
            return

        fqdn = Indicator(**i.__dict__())
        fqdn.indicator = i.is_subdomain()
        fqdn.lasttime = fqdn.reporttime = arrow.utcnow()

        try:
            resolve_itype(fqdn.indicator)
        except InvalidIndicator as e:
            self.logger.error(fqdn)
            self.logger.error(e)
        else:
            fqdn.confidence = (fqdn.confidence - 3) if fqdn.confidence >= 3 else 0
            fqdn.rdata = '{} subdomain'.format(i.indicator)
            if 'hunter' not in fqdn.tags:
                fqdn.tags.append('hunter')
            router.indicators_create(fqdn)
            self.logger.debug("FQDN Subdomain Hunter: {}".format(fqdn))


Plugin = FqdnSubdomain