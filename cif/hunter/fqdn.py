import logging
import copy
from cif.utils import resolve_ns
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
                fqdn = copy.deepcopy(i)
                fqdn.indicator = str(rr).rstrip('.')
                fqdn.itype = 'fqdn'
                fqdn.confidence = (int(fqdn.confidence) / 2)
                x = router.submit(fqdn)
                self.logger.debug(x)

            if i.is_subdomain():
                fqdn = copy.deepcopy(i)
                fqdn.indicator = i.is_subdomain()
                fqdn.confidence = (int(fqdn.confidence) / 3)
                x = router.submit(fqdn)
                self.logger.debug(x)

            r = resolve_ns(i.indicator)
            self.logger.debug(r)
            for rr in r:
                ip = copy.deepcopy(i)
                ip.indicator = str(rr)
                ip.itype = 'ipv4'
                ip.confidence = (int(ip.confidence) / 4)
                x = router.submit(ip)
                self.logger.debug(x)

            r = resolve_ns(i.indicator, t='NS')
            self.logger.debug('NS: {}'.format(r))
            for rr in r:
                ip = copy.deepcopy(i)
                ip.indicator = str(rr).rstrip('.')
                ip.itype = 'fqdn'
                ip.confidence = (int(ip.confidence) / 5)
                x = router.submit(ip)
                self.logger.debug(x)

            r = resolve_ns(i.indicator, t='MX')
            self.logger.debug('MX: {}'.format(r))
            for rr in r:
                ip = copy.deepcopy(i)
                ip.indicator = str(rr).rstrip('.')
                ip.itype = 'fqdn'
                ip.confidence = (int(ip.confidence) / 6)
                x = router.submit(ip)
                self.logger.debug(x)


Plugin = Fqdn