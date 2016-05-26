import logging
from cif.utils import resolve_ns
from csirtg_indicator import Indicator
from pprint import pprint


def is_subdomain(i):
    bits = i.split('.')
    if len(bits) > 2:
        return True


class Fqdn(object):

    def __init__(self, *args, **kv):
        self.logger = logging.getLogger(__name__)

    def process(self, i, router):
        if i.itype == 'fqdn':
            r = resolve_ns(i.indicator, t='CNAME')
            self.logger.debug('CNAME: {}'.format(r))
            for rr in r:
                fqdn = Indicator(**i.__dict__)

                fqdn.indicator = str(rr).rstrip('.')
                fqdn.itype = 'fqdn'
                fqdn.confidence = (int(fqdn.confidence) / 2)
                x = router.indicators_create(fqdn)
                self.logger.debug(x)

            if i.is_subdomain():
                fqdn = Indicator(**i.__dict__)
                fqdn.indicator = i.is_subdomain()
                fqdn.confidence = (int(fqdn.confidence) / 3)
                x = router.indicators_create(fqdn)
                self.logger.debug(x)

            r = resolve_ns(i.indicator)
            self.logger.debug(r)
            for rr in r:
                ip = Indicator(**i.__dict__)
                ip.indicator = str(rr)
                ip.itype = 'ipv4'
                ip.confidence = (int(ip.confidence) / 4)
                x = router.indicators_create(ip)
                self.logger.debug(x)

            r = resolve_ns(i.indicator, t='NS')
            self.logger.debug('NS: {}'.format(r))
            for rr in r:
                ip = Indicator(**i.__dict__)
                ip.indicator = str(rr).rstrip('.')
                ip.itype = 'fqdn'
                ip.confidence = (int(ip.confidence) / 5)
                x = router.indicators_create(ip)
                self.logger.debug(x)

            r = resolve_ns(i.indicator, t='MX')
            self.logger.debug('MX: {}'.format(r))
            for rr in r:
                ip = Indicator(**i.__dict__)
                ip.indicator = str(rr).rstrip('.')
                ip.itype = 'fqdn'
                ip.confidence = (int(ip.confidence) / 6)
                x = router.indicators_create(ip)
                self.logger.debug(x)


Plugin = Fqdn