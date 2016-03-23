import dns.resolver
import logging
import copy
from cif.utils import resolve_ns
from pprint import pprint


class Fqdn(object):

    def __init__(self, *args, **kv):
        self.logger = logging.getLogger(__name__)

    def process(self, i, router):
        if i.itype == 'fqdn':
            r = resolve_ns(i.indicator)
            self.logger.debug(r)
            for rr in r:
                ip = copy.deepcopy(i)
                ip.indicator = str(rr)
                ip.itype = 'ipv4'
                ip.confidence = (int(ip.confidence) / 2)
                x = router.submit(ip)
                self.logger.debug(x)

            r = resolve_ns(i.indicator, t='CNAME')
            self.logger.debug(r)
            for rr in r:
                ip = copy.deepcopy(i)
                ip.indicator = str(rr).rstrip('.')
                ip.itype = 'fqdn'
                ip.confidence = (int(ip.confidence) / 2)
                x = router.submit(ip)
                self.logger.debug(x)

            r = resolve_ns(i.indicator, t='NS')
            self.logger.debug(r)
            for rr in r:
                ip = copy.deepcopy(i)
                ip.indicator = str(rr).rstrip('.')
                ip.itype = 'fqdn'
                ip.confidence = (int(ip.confidence) / 3)
                x = router.submit(ip)
                self.logger.debug(x)

            r = resolve_ns(i.indicator, t='MX')
            for rr in r:
                ip = copy.deepcopy(i)
                ip.indicator = str(rr).rstrip('.')
                ip.itype = 'fqdn'
                ip.confidence = (int(ip.confidence) / 4)
                x = router.submit(ip)
                self.logger.debug(x)


Plugin = Fqdn