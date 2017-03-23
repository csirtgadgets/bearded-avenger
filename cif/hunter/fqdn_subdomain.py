import logging
from csirtg_indicator import Indicator
from csirtg_indicator import resolve_itype
from csirtg_indicator.exceptions import InvalidIndicator


class FqdnSubdomain(object):

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.is_advanced = False

    def process(self, i, router):
        if i.itype != 'fqdn':
            return

        if 'search' in i.tags:
            return

        if not i.is_subdomain():
            return

        fqdn = Indicator(**i.__dict__())
        fqdn.indicator = i.is_subdomain()

        try:
            resolve_itype(fqdn.indicator)
        except InvalidIndicator as e:
            self.logger.error(fqdn)
            self.logger.error(e)
        else:
            fqdn.confidence = (fqdn.confidence - 3) if fqdn.confidence >= 3 else 0
            router.indicators_create(fqdn)

Plugin = FqdnSubdomain
