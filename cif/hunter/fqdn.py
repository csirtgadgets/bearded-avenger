import logging
from cif.utils import resolve_ns
from csirtg_indicator import Indicator
from dns.resolver import Timeout
from pprint import pprint
from cifsdk.constants import PYVERSION
from csirtg_indicator import resolve_itype
from csirtg_indicator.exceptions import InvalidIndicator
import re
import arrow


class Fqdn(object):

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.is_advanced = True

    def process(self, i, router, **kwargs):
        if i.itype != 'fqdn':
            return

        if 'search' in i.tags:
            return

        try:
            r = resolve_ns(i.indicator)
        except Timeout:
            self.logger.info('timeout trying to resolve: {}'.format(i.indicator))
            return

        for rr in r:
            rr = str(rr)
            if rr in ["", 'localhost', '0.0.0.0']:
                continue

            ip = Indicator(**i.__dict__())
            ip.lasttime = ip.reporttime = arrow.utcnow()

            ip.indicator = rr
            try:
                resolve_itype(ip.indicator)
            except InvalidIndicator as e:
                self.logger.error(ip)
                self.logger.error(e)
            else:
                ip.itype = 'ipv4'
                ip.rdata = i.indicator
                ip.tags = ['pdns', 'hunter']
                ip.confidence = 10
                router.indicators_create(ip)
                self.logger.debug("FQDN Hunter: {}".format(ip))


Plugin = Fqdn
