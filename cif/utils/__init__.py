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
        answers = resolver.resolve(data, t)
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

def strtobool(val):
    """
    reimplementation of distutils.util.strtobool which is being deprecated
    :param val: value to check. True values are y, yes, t, true, on, and 1; false values are n,
        no, f, false, off, and 0. Raises ValueError if val is anything else.
    
    :return: bool True or False
    """
    val = str(val).lower()
    if val in ('y', 'yes', 't', 'true', 'on', '1'):
        return True
    elif val in ('n', 'no', 'f', 'false', 'off', '0'):
        return False
    else:
        raise ValueError('invalid truth value {!r}'.format(val))
