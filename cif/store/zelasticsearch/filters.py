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
    if mask < 28:
        raise InvalidSearch('prefix needs to be greater than or equal to 28')

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

    high = 'now/m'
    # if passed 'days' or 'hours', preferentially use that for ES filtering/caching
    if filter.get('days') or filter.get('hours'):
        if filter.get('hours'):
            lookback_amount = filter.pop('hours')
            lookback_unit = 'h'
        elif filter.get('days'):
            lookback_amount = filter.pop('days')
            lookback_unit = 'd'

        try:
            lookback_amount = int(lookback_amount)
        except Exception as e:
            raise InvalidSearch('Lookback time filter {}{} is not a valid time'.format(lookback_amount, lookback_unit))

        # don't put spaces in relative date math operator query to make it easier to read. ES hates that and will error.
        low = 'now/m-{}{}'.format(lookback_amount, lookback_unit)
    # no relative 'days' or 'hours' params, so fallback to 'reporttime'
    else:
        c = filter.pop('reporttime')
        if PYVERSION == 2:
            if type(c) == unicode:
                c = str(c)

        if isinstance(c, basestring) and ',' in c:
            low, high = c.split(',')
        else:
            low = c

        low = arrow.get(low).datetime

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


def filter_rdata(s, q_filters):
    if not q_filters.get('rdata'):
        return s

    r = q_filters.pop('rdata')

    # limit number of wildcards that can be used to mitigate ES query performance degradation
    if '*' in r and r.count('*') <= 2:
        return s.query("wildcard", rdata=r)

    s = s.filter("term", rdata=r)
    return s


def filter_terms(s, q_filters):
    for f in q_filters:
        if f in ['nolog', 'days', 'hours', 'groups', 'limit', 'provider', 'reporttime', 'tags']:
            continue

        kwargs = {f: q_filters[f]}
        if isinstance(q_filters[f], list):
            s = s.filter('terms', **kwargs)
        else:
            s = s.filter('term', **kwargs)

    return s


def filter_tags(s, q_filters):
    if not q_filters.get('tags'):
        return s

    tags = q_filters.pop('tags')

    if isinstance(tags, basestring):
        tags = [x.strip() for x in tags.split(',')]

    # each array element is implicitly ORed (aka, 'should') using a terms filter
    #s = s.filter('terms', tags=tags)
    tt = []
    not_tt = []
    for t in tags:
        # used for tags exclusion/negation
        if t.startswith('!'):
            t = t[1:]
            not_tt.append(t)
        else:
            tt.append(t)

    if len(not_tt) > 0:
        if len(not_tt) == 1:
            s = s.exclude('term', tags=not_tt[0])
        else:
            s = s.exclude('terms', tags=not_tt)

    if len(tt) > 0:
        if len(tt) == 1:
            s = s.filter('term', tags=tt[0])
        else:
            s = s.filter('terms', tags=tt)

    return s

def filter_provider(s, q_filters):
    if not q_filters.get('provider'):
        return s

    provider = q_filters.pop('provider')

    if isinstance(provider, basestring):
        provider = [x.strip() for x in provider.split(',')]

    pp = []
    not_pp = []
    for p in provider:
        # used for provider exclusion/negation
        if p.startswith('!'):
            p = p[1:]
            not_pp.append(p)
        else:
            pp.append(p)

    if len(not_pp) > 0:
        if len(not_pp) == 1:
            s = s.exclude('term', provider=not_pp[0])
        else:
            s = s.exclude('terms', provider=not_pp)

    if len(pp) > 0:
        if len(pp) == 1:
            s = s.filter('term', provider=pp[0])
        else:
            s = s.filter('terms', provider=pp)

    return s


def filter_groups(s, q_filters, token=None):
    if token:
        groups = token.get('groups', 'everyone')
    else:
        groups = q_filters.pop('groups')

    if isinstance(groups, basestring):
        groups = [groups]

    # each array element is implicitly ORed (aka, 'should') using a terms filter
    s = s.filter('terms', group=groups)

    return s

def filter_id(s, q_filters):
    if not q_filters.get('id'):
        return s

    id = q_filters.pop('id')

    s.query = Q('match_phrase', uuid=id)

    return s

def filter_build(s, filters, token=None):
    limit = filters.get('limit')
    if limit and int(limit) > WINDOW_LIMIT:
        raise InvalidSearch('Request limit should be <= server threshold of {} but was set to {}'.format(WINDOW_LIMIT, limit))

    q_filters = {}
    for f in VALID_FILTERS:
        if filters.get(f):
            q_filters[f] = filters[f]

    s = filter_provider(s, q_filters)

    s = filter_confidence(s, q_filters)

    s = filter_id(s, q_filters)

    s = filter_rdata(s, q_filters)

    # treat indicator as special, transform into Search
    s = filter_indicator(s, q_filters)

    s = filter_reporttime(s, q_filters)

    # transform all other filters into term=
    s = filter_terms(s, q_filters)

    if q_filters.get('groups'):
        s = filter_groups(s, q_filters)
    else:
        if token and (not token.get('admin') or token.get('admin') == ''):
            s = filter_groups(s, {}, token=token)

    if q_filters.get('tags'):
        s = filter_tags(s, q_filters)

    return s
