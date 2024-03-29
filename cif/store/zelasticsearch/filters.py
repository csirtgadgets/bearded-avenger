from csirtg_indicator.utils import resolve_itype
import socket
from cifsdk.exceptions import InvalidSearch
from csirtg_indicator.exceptions import InvalidIndicator
import binascii
from cifsdk.constants import PYVERSION
from elasticsearch_dsl import Q
import arrow
from collections import OrderedDict

from cif.store.zelasticsearch.constants import WINDOW_LIMIT
from cif.store.zelasticsearch.helpers import cidr_to_range
from cif.httpd.common import VALID_FILTERS
from cif.store.zelasticsearch.constants import UPSERT_MATCH

OPTIONAL_AND_USER_SPECIFIABLE_FIELDS = {
    'application', 'description', 'portlist', 'protocol', 'rdata', 'reference',
}

FILTER_TERMS_EXCLUDE_FIELDS = {
    'nolog', 'days', 'hours', 'groups', 'limit', 'provider', 'reporttime', 'reporttimeend', 'tags', 
    'find_relatives',
}

# compare user configured UPSERT_MATCH fields against optional indicator fields.
# any commonalities should be checked in an upsert search b/c, if it's not specified in
# the search, the field shouldn't exist in potential upsert targets to prevent returning 
# a match against an indicator that has that field
# set when the search was for an indicator without that field at all.
# this is only a potential issue for optional indicator fields which is why we only compare
# against those
FIELDS_TO_CHECK_FOR_NARROW_QUERY = OPTIONAL_AND_USER_SPECIFIABLE_FIELDS.intersection(UPSERT_MATCH)

if PYVERSION > 2:
    basestring = (str, bytes)


def _filter_ipv4(s, i, find_relatives=False):
    start, end, mask = cidr_to_range(i)
    if mask < 8:
        raise InvalidSearch('prefix needs to be greater than or equal to 8')

    # if doing a regular search, match only the exact CIDR or single IP provided
    if not find_relatives:
        return s.filter('term', indicator=i)

    # for single IP search, find exact IP or any parent CIDRs
    # for CIDR search, find exact CIDR, parent CIDRs, child CIDRs, or any single IPs contained within specified CIDR
    indicator_hit = Q('range', indicator_ipv4={'gte': start, 'lte': end})
    iprange_hit = Q('range', indicator_iprange={'gte': start, 'lte': end})

    s = s.filter(indicator_hit | iprange_hit)
    return s

def _filter_url(s, i):
    # resolve_itype sees www.place.tld/* as valid url, but it was likely intended as wildcard search
    if i.endswith('*'):
        s = s.query('wildcard', indicator=i)
        return s

    s = s.filter('term', indicator=i)
    return s

def _filter_ipv6(s, i, find_relatives=False):
    start, end, mask = cidr_to_range(i)
    if mask < 28:
        raise InvalidSearch('prefix needs to be greater than or equal to 28')

    if not find_relatives:
        return s.filter('term', indicator=i)

    start_flattened = binascii.b2a_hex(socket.inet_pton(
        socket.AF_INET6, start)).decode('utf-8')
    end_flattened = binascii.b2a_hex(socket.inet_pton(
        socket.AF_INET6, end)).decode('utf-8')

    indicator_hit = Q('range', indicator_ipv6={'gte': start_flattened, 'lte': end_flattened})
    iprange_hit = Q('range', indicator_iprange={'gte': start, 'lte': end})

    s = s.filter(indicator_hit | iprange_hit)
    return s


def _filter_ssdeep(s, i, find_relatives=False):
    # https://www.intezer.com/blog/malware-analysis/intezer-community-tip-ssdeep-comparisons-with-elasticsearch/
    # if doing a regular search, match only the exact hash
    if not find_relatives:
        return s.filter('term', indicator=i)

    # extract chunks from indicator for fuzzy search
    chunksize, chunk, double_chunk = i.split(':')
    chunksize = int(chunksize)

    s = s.filter('terms', 
        indicator_ssdeep_chunksize=[chunksize, chunksize * 2, int(chunksize / 2)]
        )

    exact_hit = chunk_hit = Q('match', indicator=i)
    chunk_hit = Q('match', indicator_ssdeep_chunk=chunk)
    double_chunk_hit = Q('match', indicator_ssdeep_double_chunk=double_chunk)

    s = s.filter(exact_hit | chunk_hit | double_chunk_hit)
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
        low = filter.pop('reporttime')
        if PYVERSION == 2:
            if type(low) == unicode:
                low = str(low)

        if filter.get('reporttimeend'):
            high = filter.pop('reporttimeend')

    s = s.filter('range', reporttime={'gte': low, 'lte': high})
    return s


def filter_indicator(s, filters, find_relatives=False):
    if not filters.get('indicator'):
        return s

    i = filters.pop('indicator')

    try:
        itype = resolve_itype(i)
    except InvalidIndicator:
        if '%' in i:
            i = i.replace('%', '*')

        if '*' in i:
            return s.query("wildcard", indicator=i)

        s = s.query("match", message=i)
        return s

    if itype in ('email', 'fqdn', 'md5', 'sha1', 'sha256', 'sha512'):
        s = s.filter('term', indicator=i)
        return s

    if itype == 'ipv4':
        return _filter_ipv4(s, i, find_relatives)

    if itype == 'ipv6':
        return _filter_ipv6(s, i, find_relatives)
    
    if itype == 'url':
        return _filter_url(s, i)
    
    if itype == 'ssdeep':
        return _filter_ssdeep(s, i, find_relatives)

    return s


def filter_rdata(s, filters):
    if not filters.get('rdata'):
        return s

    r = filters.pop('rdata')

    # limit number of wildcards that can be used to mitigate ES query performance degradation
    if '*' in r and r.count('*') <= 2:
        return s.query("wildcard", rdata=r)

    s = s.filter("term", rdata=r)
    return s


def filter_terms(s, filters):
    for f in filters:
        if f in FILTER_TERMS_EXCLUDE_FIELDS:
            continue

        kwargs = {f: filters[f]}
        if isinstance(filters[f], list):
            s = s.filter('terms', **kwargs)
        else:
            s = s.filter('term', **kwargs)

    return s


def filter_tags(s, filters, narrow_query=False):
    if not filters.get('tags'):
        return s

    tags = filters.pop('tags')

    if isinstance(tags, basestring):
        tags = {x.strip() for x in tags.split(',')}

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

    # if tags need to be explicitly AND'd together rather than the normal OR 
    # (upsert searches)
    if narrow_query:
        if len(tt) > 0:
            for tag in tt:
                s = s.filter('term', tags=tag)

            s = s.filter('script', 
                script='doc["tags"].values.length == {}'.format(len(tt)))

        return s
    
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

def filter_provider(s, filters):
    if not filters.get('provider'):
        return s

    provider = filters.pop('provider')

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


def filter_groups(s, filters, token=None):
    if token:
        groups = token.get('groups', 'everyone')
    else:
        groups = filters.pop('groups')

    if isinstance(groups, basestring):
        groups = [groups]

    # each array element is implicitly ORed (aka, 'should') using a terms filter
    s = s.filter('terms', group=groups)

    return s

def filter_id(s, filters):
    if not filters.get('id'):
        return s

    id = filters.pop('id').lower()

    s = s.filter('term', **{'uuid.keyword': id})

    return s

def filter_sort(s, filters):
    if not filters.get('sort'):
        return s.sort('-reporttime', '-lasttime')

    sort = filters.pop('sort')

    if isinstance(sort, basestring):
        sort = [x.strip() for x in sort.split(',')] # can't make this a set b/c it doesn't preserve order
    else:
        return s.sort('-reporttime', '-lasttime')

    # use ordered dict for easy column name uniqueness and asc/desc lookup later
    filtered_sort = OrderedDict()

    # only ever iterate through max 2 elements, no matter how many csvs were given
    for col_name in sort[:2]:
        if col_name.startswith('-'):
            direction = '-'
            col_name = col_name[1:]
        else:
            direction = ''

        if col_name in VALID_FILTERS and col_name not in filtered_sort:
            filtered_sort[col_name] = direction

    if len(filtered_sort) == 0:
        s = s.sort('-reporttime', '-lasttime')
    elif len(filtered_sort) == 1:
        column_name, direction = list(filtered_sort.items())[0]
        s = s.sort('{}{}'.format(direction, column_name))
    elif len(filtered_sort) >= 2:
        col1, col2 = list(filtered_sort.items())[:2]
        col1_name = col1[0]
        col1_dir = col1[1]
        col2_name = col2[0]
        col2_dir = col2[1]
        # create the final sort e.g., sort('-reporttime', 'confidence')
        s = s.sort('{}{}'.format(col1_dir, col1_name), '{}{}'.format(col2_dir, col2_name))

    return s

def filter_fields(s, fields_to_exclude):
    for field in fields_to_exclude:
        s = s.exclude('exists', field=field)
    return s

def filter_build(s, filters, token=None, find_relatives=False, narrow_query=False):
    limit = filters.get('limit')
    if limit and int(limit) > WINDOW_LIMIT:
        raise InvalidSearch('Request limit should be <= server threshold of {} but was set to {}'.format(WINDOW_LIMIT, limit))

    if narrow_query:
        fields_must_not_exist = FIELDS_TO_CHECK_FOR_NARROW_QUERY.difference(filters.keys())
        s = filter_fields(s, fields_must_not_exist)

    s = filter_sort(s, filters)
    
    s = filter_provider(s, filters)

    s = filter_confidence(s, filters)

    s = filter_id(s, filters)

    s = filter_rdata(s, filters)

    # treat indicator as special, transform into Search
    s = filter_indicator(s, filters, find_relatives)

    s = filter_reporttime(s, filters)

    if filters.get('groups'):
        s = filter_groups(s, filters)
    else:
        if token and (not token.get('admin') or token.get('admin') == ''):
            s = filter_groups(s, {}, token=token)

    if filters.get('tags'):
        s = filter_tags(s, filters, narrow_query)

    # transform all other filters into term=
    s = filter_terms(s, filters)

    return s
