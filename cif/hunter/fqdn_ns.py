import logging
from csirtg_indicator import resolve_itype
from csirtg_indicator.exceptions import InvalidIndicator
from cif.utils import resolve_ns
from csirtg_indicator import Indicator
from dns.resolver import Timeout
import arrow


class FqdnNs(object):

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.is_advanced = True

    def process(self, i, router, **kwargs):
        if i.itype != 'fqdn':
            return

        if 'search' in i.tags:
            return

        try:
            r = resolve_ns(i.indicator, t='NS')
        except Timeout:
            self.logger.info('timeout trying to resolve: {}'.format(i.indicator))
            return

        for rr in r:
            rr = str(rr).rstrip('.')
            if rr in ["", 'localhost', '0.0.0.0']:
                continue

            i_ns = Indicator(**i.__dict__())
            i_ns.indicator = rr

            try:
                i_ns_itype = resolve_itype(i_ns.indicator)
            except InvalidIndicator as e:
                self.logger.error(i_ns)
                self.logger.error(e)
            else:
                i_ns.lasttime = i_ns.reporttime = arrow.utcnow()
                i_ns.itype = i_ns_itype
                i_ns.rdata = "{} nameserver".format(i.indicator)
                if 'hunter' not in i_ns.tags:
                    i_ns.tags.append('hunter')
                i_ns.confidence = (i_ns.confidence - 4) if i_ns.confidence >= 4 else 0
                router.indicators_create(i_ns)
                self.logger.debug("FQDN NS Hunter: {}".format(i_ns))

Plugin = FqdnNs
