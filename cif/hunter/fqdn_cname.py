import logging
from cif.utils import resolve_ns
from csirtg_indicator import Indicator
from dns.resolver import Timeout
from csirtg_indicator import resolve_itype
from csirtg_indicator.exceptions import InvalidIndicator
import arrow

class FqdnCname(object):

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.is_advanced = True

    def process(self, i, router):
        if i.itype != 'fqdn':
            return

        if 'search' in i.tags:
            return

        try:
            r = resolve_ns(i.indicator, t='CNAME')
        except Timeout:
            self.logger.info('timeout trying to resolve: {}'.format(i.indicator))
            r = []

        for rr in r:
            # http://serverfault.com/questions/44618/is-a-wildcard-cname-dns-record-valid
            rr = str(rr).rstrip('.').lstrip('*.')
            if rr in ['', 'localhost', '0.0.0.0']:
                continue

            fqdn = Indicator(**i.__dict__())
            fqdn.indicator = rr
            fqdn.lasttime = fqdn.reporttime = arrow.utcnow()

            try:
                resolve_itype(fqdn.indicator)
            except InvalidIndicator as e:
                self.logger.error(fqdn)
                self.logger.error(e)
                return

            fqdn.itype = 'fqdn'
            if 'hunter' not in fqdn.tags:
                fqdn.tags.append('hunter')
            if fqdn.confidence < 8:
                fqdn.confidence -= 1
            else:
                fqdn.confidence = 7
            router.indicators_create(fqdn)

Plugin = FqdnCname
