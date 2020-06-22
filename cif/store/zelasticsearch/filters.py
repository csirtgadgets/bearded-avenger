from csirtg_indicator.utils import resolve_itype
import socket
from cifsdk.exceptions import InvalidSearch
from csirtg_indicator.exceptions import InvalidIndicator
import binascii
from cifsdk.constants import PYVERSION
from elasticsearch_dsl import Q
import ipaddress
import arrow

from cif.store.zelasticsearch.constants import WINDOW_LIMIT
from cif.httpd.common import VALID_FILTERS


if PYVERSION > 2:
    basestring = (str, bytes)


def _filter_ipv4(s, i):
    ip = ipaddress.IPv4Network(i)
    mask = ip.prefixlen
    if mask < 8:
        raise InvalidSearch('prefix needs to be greater than or equal to 8')

    start = str(ip.network_address)
    end = str(ip.broadcast_address)

    s = s.filter('range', indicator_ipv4={'gte': start, 'lte': end})
    return s


def _filter_ipv6(s, i):
    ip = ipaddress.IPv6Network(i)
    mask = ip.prefixlen
    if mask < 32:
        raise InvalidSearch('prefix needs to be greater than or equal to 32')

    start = binascii.b2a_hex(socket.inet_pton(
        socket.AF_INET6, str(ip.network_address))).decode('utf-8')
    end = binascii.b2a_hex(socket.inet_pton(
        socket.AF_INET6, str(ip.broadcast_address))).decode('utf-8')

    s = s.filter('range', indicator_ipv6={'gte': start, 'lte': end})
    return s


def filter_confidence(s, filter):
    if not filter.get('confidence'):
        return s

    c = filter.pop('confidence')
    if PYVERSION == 2:
        if type(c) == unicode:
            c = str(c)

    low, high = c, 10.0
    if isinstance(c, basestring) and ',' in c:
        low, high = c.split(',')

    s = s.filter('range', confidence={'gte': float(low), 'lte': float(high)})
    return s


def filter_reporttime(s, filter):
    if not filter.get('reporttime'):
        return s

    c = filter.pop('reporttime')
    if PYVERSION == 2:
        if type(c) == unicode:
            c = str(c)

    low, high = c, arrow.utcnow()
    if isinstance(c, basestring) and ',' in c:
        low, high = c.split(',')

    low = arrow.get(low).datetime
    high = arrow.get(high).datetime

    s = s.filter('range', reporttime={'gte': low, 'lte': high})
    return s


def filter_indicator(s, q_filters):
    if not q_filters.get('indicator'):
        return s

    i = q_filters.pop('indicator')

    try:
        itype = resolve_itype(i)
    except InvalidIndicator:
        if '%' in i:
            i = i.replace('%', '*')

        if '*' in i:
            return s.query("wildcard", indicator=i)

        s = s.query("match", message=i)
        return s

    if itype in ('email', 'url', 'fqdn', 'md5', 'sha1', 'sha256', 'sha512'):
        s = s.filter('term', indicator=i)
        return s

    if itype is 'ipv4':
        return _filter_ipv4(s, i)

    if itype is 'ipv6':
        return _filter_ipv6(s, i)

    return s


def filter_terms(s, q_filters):
    for f in q_filters:
        if f in ['nolog', 'days', 'hours', 'groups', 'limit', 'tags']:
            continue

        kwargs = {f: q_filters[f]}
        if isinstance(q_filters[f], list):
            s = s.filter('terms', **kwargs)
        else:
            s = s.filter('term', **kwargs)

    return s


def filter_tags(s, q_filters):
    tags = q_filters['tags']

    if isinstance(tags, basestring):
        tags = tags.split(',')

    tt = []
    for t in tags:
        tt.append(Q('term', tags=t))

    s.query = Q('bool', must=s.query, should=tt, minimum_should_match=1)

    return s


def filter_groups(s, q_filters, token=None):
    if token:
        groups = token.get('groups', 'everyone')
    else:
        groups = q_filters['groups']

    if isinstance(groups, basestring):
        groups = [groups]

    gg = []
    for g in groups:
        gg.append(Q('term', group=g))

    s.query = Q('bool', must=s.query, should=gg, minimum_should_match=1)

    return s

def filter_id(s, q_filters):
    if not q_filters.get('id'):
        return s

    id = q_filters.pop('id')

    s.query = Q('match_phrase', uuid=id)

    return s

def filter_build(s, filters, token=None):
    limit = filters.get('limit')
    if limit and limit > WINDOW_LIMIT:
        raise InvalidSearch('request limit should be <= server threshold of {} but was set to {}'.format(WINDOW_LIMIT, limit))
        
    q_filters = {}
    for f in VALID_FILTERS:
        if filters.get(f):
            q_filters[f] = filters[f]

    # treat indicator as special, transform into Search
    s = filter_indicator(s, q_filters)

    s = filter_id(s, q_filters)

    s = filter_confidence(s, q_filters)

    s = filter_reporttime(s, q_filters)

    # transform all other filters into term=
    s = filter_terms(s, q_filters)

    if filters.get('tags'):
        s = filter_tags(s, filters)

    if filters.get('groups'):
        s = filter_groups(s, filters)
    else:
        if token:
            s = filter_groups(s, {}, token=token)

    return s
