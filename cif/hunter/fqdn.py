import dns.resolver
import logging
import copy
import dns.resolver
from dns.resolver import NoAnswer, NXDOMAIN
from pprint import pprint


class Fqdn(object):

    def __init__(self, *args, **kv):
        self.logger = logging.getLogger(__name__)

    def _resolve(self, data, t='A'):
        answers = dns.resolver.query(data, t)
        resp = []
        for rdata in answers:
            self.logger.debug(rdata)
            resp.append(rdata)
        return resp

    def _resolve_mx(self, data):
        r = self._resolve(data, 'MX')
        return [rr.exchange for rr in r]

    def _resolve_ns(self, data):
        return self._resolve(data, 'NS')

    def process(self, i, router):
        if i.itype == 'fqdn':
            try:
                r = self._resolve(i.indicator)
                for rr in r:
                    ip = copy.deepcopy(i)
                    ip.indicator = str(rr)
                    ip.itype = 'ipv4'
                    ip.confidence = (int(ip.confidence) / 2)
                    x = router.submit(ip)
                    self.logger.debug(x)
            except (NoAnswer, NXDOMAIN):
                self.logger.info('no answer for {}'.format(i.indicator))

            try:
                r = self._resolve_ns(i.indicator)
                for rr in r:
                    ip = copy.deepcopy(i)
                    ip.indicator = str(rr)
                    ip.itype = 'ipv4'
                    ip.confidence = (int(ip.confidence) / 3)
                    x = router.submit(ip)
                    self.logger.debug(x)
            except (NoAnswer, NXDOMAIN):
                self.logger.info('no NS answer for {}'.format(i.indicator))

            try:
                r = self._resolve_mx(i.indicator)
                for rr in r:
                    ip = copy.deepcopy(i)
                    ip.indicator = str(rr)
                    ip.itype = 'ipv4'
                    ip.confidence = (int(ip.confidence) / 4)
                    x = router.submit(ip)
                    self.logger.debug(x)
            except (NoAnswer, NXDOMAIN):
                self.logger.info('no MX answer for {}'.format(i.indicator))


Plugin = Fqdn