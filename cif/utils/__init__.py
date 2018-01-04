import dns.resolver
from dns.resolver import NoAnswer, NXDOMAIN, NoNameservers, Timeout
from dns.name import EmptyLabel
from cif.constants import HUNTER_RESOLVER_TIMEOUT
import logging

logger = logging.getLogger(__name__)


def resolve_ns(data, t='A', timeout=HUNTER_RESOLVER_TIMEOUT):
    resolver = dns.resolver.Resolver()
    resolver.timeout = timeout
    resolver.lifetime = timeout
    resolver.search = []
    try:
        answers = resolver.query(data, t)
        resp = []
        for rdata in answers:
            resp.append(rdata)
    except (NoAnswer, NXDOMAIN, EmptyLabel, NoNameservers, Timeout) as e:
        if str(e).startswith('The DNS operation timed out after'):
            logger.info('{} - {} -- this may be normal'.format(data, e))
            return []

        if not str(e).startswith('The DNS response does not contain an answer to the question'):
            if not str(e).startswith('None of DNS query names exist'):
                logger.info('{} - {}'.format(data, e))
        return []

    return resp
