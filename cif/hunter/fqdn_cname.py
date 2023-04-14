import logging
from cif.utils import resolve_ns
from cif.hunter import HUNTER_MIN_CONFIDENCE
from csirtg_indicator import Indicator
from dns.resolver import Timeout
from csirtg_indicator import resolve_itype
from csirtg_indicator.exceptions import InvalidIndicator
import arrow

class FqdnCname(object):

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.is_advanced = True
        self.mtypes_supported = { 'indicators_create' }
        self.itypes_supported = { 'fqdn' }

    def _prereqs_met(self, i, **kwargs):
        if kwargs.get('mtype') not in self.mtypes_supported:
            return False
            
        if i.itype not in self.itypes_supported:
            return False

        if 'search' in i.tags:
            return False

        return True

    def process(self, i, router, **kwargs):
        if not self._prereqs_met(i, **kwargs):
            return

        try:
            r = resolve_ns(i.indicator, t='CNAME')
        except Timeout:
            self.logger.info('timeout trying to resolve: {}'.format(i.indicator))
            return

        for rr in r:
            # http://serverfault.com/questions/44618/is-a-wildcard-cname-dns-record-valid
            rr = str(rr).rstrip('.').lstrip('*.')
            if rr in ['', 'localhost', '0.0.0.0']:
                continue

            cname = Indicator(**i.__dict__())
            cname.indicator = rr
            cname.lasttime = cname.reporttime = arrow.utcnow()

            try:
                resolve_itype(cname.indicator)
            except InvalidIndicator as e:
                self.logger.error(cname)
                self.logger.error(e)
                return

            cname.itype = 'fqdn'
            cname.rdata = '{} cname'.format(i.indicator)
            if 'hunter' not in cname.tags:
                cname.tags.append('hunter')
            # prevent hunters from running on insertion of this cname
            cname.confidence = max(0, min(cname.confidence, HUNTER_MIN_CONFIDENCE - 1))
            router.indicators_create(cname)
            self.logger.debug("FQDN CNAME Hunter: {}".format(cname))


Plugin = FqdnCname