from elasticsearch_dsl import DocType, String, Date, Integer, Float, Ip, Mapping, Index, GeoPoint, Byte

import elasticsearch.exceptions
from elasticsearch_dsl.connections import connections
import os
from pprint import pprint
from cifsdk.exceptions import AuthError, InvalidSearch
from csirtg_indicator import resolve_itype
from csirtg_indicator.exceptions import InvalidIndicator
from datetime import datetime
import ipaddress
import arrow
import re
from base64 import b64decode
import binascii
import socket
import logging

VALID_FILTERS = ['indicator', 'confidence', 'provider', 'itype', 'group', 'tags', 'rdata']

LIMIT = 5000
LIMIT = os.getenv('CIF_ES_LIMIT', LIMIT)

LIMIT_HARD = 500000
LIMIT_HARD = os.getenv('CIF_ES_LIMIT_HARD', LIMIT_HARD)

TIMEOUT = '120'
TIMEOUT = os.getenv('CIF_ES_TIMEOUT', TIMEOUT)
TIMEOUT = '{}s'.format(TIMEOUT)

logger = logging.getLogger('cif.store.zelasticsearch')


class Indicator(DocType):
    indicator = String(index="not_analyzed")
    indicator_ipv4 = Ip()
    indicator_ipv6 = String(index='not_analyzed')
    indicator_ipv6_mask = Integer()
    group = String(multi=True, index="not_analyzed")
    itype = String(index="not_analyzed")
    tlp = String(index="not_analyzed")
    provider = String(index="not_analyzed")
    portlist = String()
    asn = Float()
    asn_desc = String()
    cc = String(fields={'raw': String(index='not_analyzed')})
    protocol = String(fields={'raw': String(index='not_analyzed')})
    reporttime = Date()
    lasttime = Date()
    firsttime = Date()
    confidence = Integer()
    timezone = String()
    city = String(fields={'raw': String(index='not_analyzed')})
    description = String(index="not_analyzed")
    tags = String(multi=True, fields={'raw': String(index='not_analyzed')})
    rdata = String(index="not_analyzed")
    count = Integer()
    message = String(multi=True)


def _current_index():
    dt = datetime.utcnow()
    dt = dt.strftime('%Y.%m')
    idx = '{}-{}'.format('indicators', dt)
    return idx


def _create_index():
    # https://github.com/csirtgadgets/massive-octo-spice/blob/develop/elasticsearch/observables.json
    # http://elasticsearch-py.readthedocs.org/en/master/api.html#elasticsearch.Elasticsearch.bulk
    idx = _current_index()
    es = connections.get_connection()
    if not es.indices.exists(idx):
        index = Index(idx)
        index.aliases(live={})
        index.doc_type(Indicator)
        index.create()

        m = Mapping('indicator')
        m.field('indicator_ipv4', 'ip')
        m.field('indicator_ipv4_mask', 'integer')
        m.field('lasttime', 'date')
        m.save(idx)
    return idx


class IndicatorMixin(object):

    def _timestamps_fix(self, i):
        if not i.get('lasttime'):
            i['lasttime'] = arrow.utcnow().datetime

        if not i.get('firsttime'):
            i['firsttime'] = i['lasttime']

        if not i.get('reporttime'):
            i['reporttime'] = arrow.utcnow().datetime

    def _is_newer(self, i, rec):
        if not i.get('lasttime'):
            return False

        i_last = arrow.get(i['lasttime']).datetime
        rec_last = arrow.get(rec['lasttime']).datetime

        if i_last > rec_last:
            return True

    def _expand_ip_idx(self, data):
        itype = resolve_itype(data['indicator'])
        if itype is 'ipv4':
            match = re.search('^(\S+)\/(\d+)$', data['indicator'])
            if match:
                data['indicator_ipv4'] = match.group(1)
                data['indicator_ipv4_mask'] = match.group(2)
            else:
                data['indicator_ipv4'] = data['indicator']

        elif itype is 'ipv6':
            match = re.search('^(\S+)\/(\d+)$', data['indicator'])
            if match:

                data['indicator_ipv6'] = binascii.b2a_hex(socket.inet_pton(socket.AF_INET6, match.group(1))).decode(
                    'utf-8')
                data['indicator_ipv6_mask'] = match.group(2)
            else:
                data['indicator_ipv6'] = binascii.b2a_hex(socket.inet_pton(socket.AF_INET6, data['indicator'])).decode(
                    'utf-8')

    def indicators_create(self, data, raw=False):
        index = _create_index()

        data['meta'] = {}
        data['meta']['index'] = index

        self._expand_ip_idx(data)

        if data.get('group') and type(data['group']) != list:
            data['group'] = [data['group']]

        if data.get('message'):
            try:
                data['message'] = str(b64decode(data['message']))
            except (TypeError, binascii.Error) as e:
                pass

        i = Indicator(**data)

        if not i.save():
            raise AuthError('invalid token')

        if raw:
            return i

        return i.to_dict()

    def indicators_upsert(self, indicators):
        count = 0
        was_added = {}  # to deal with es flushing

        es = connections.get_connection()

        if isinstance(indicators, dict):
            indicators = [indicators]

        for d in indicators:

            filters = {
                'indicator': d['indicator'],
                'provider': d['provider'],
                'limit': 1
            }

            if d.get('tags'):
                filters['tags'] = d['tags']

            if d.get('rdata'):
                filters['rdata'] = d['rdata']

            rv = list(self.indicators_search(filters, sort='reporttime', raw=True))

            if len(rv) == 0:
                if was_added.get(d['indicator']):
                    if d.get('lasttime') in was_added[d['indicator']]:
                        logger.debug('skipping: %s' % d['indicator'])
                        continue
                else:
                    was_added[d['indicator']] = set()

                if not d.get('count'):
                    d['count'] = 1

                self._timestamps_fix(d)

                self.indicators_create(d)
                es.indices.flush(index=_current_index())
                was_added[d['indicator']].add(d['lasttime'])
                count += 1
                continue

            r = rv[0]
            if not self._is_newer(d, r['_source']):
                continue

            # carry the index'd data forward and remove the old index
            i = es.get(index=r['_index'], doc_type='indicator', id=r['_id'])
            i = i['_source']

            if r['_index'] == _current_index():
                i['count'] += 1
                i['lasttime'] = d['lasttime']
                i['reporttime'] = d['lasttime']

                if d.get('message'):
                    if not i.get('message'):
                        i['message'] = []

                    i['message'].append(d['message'])

                es.update(index=r['_index'], doc_type='indicator', id=r['_id'], body={'doc': i}, refresh=True)
                continue

            # carry the information forward
            d['count'] = i['count'] + 1
            i['lasttime'] = d['lasttime']
            i['reporttime'] = d['lasttime']

            if d.get('message'):
                if not i.get('message'):
                    i['message'] = []

                i['message'].append(d['message'])

            self.indicators_create(d)
            es.delete(index=r['_index'], doc_type='indicator', id=r['_id'], refresh=True)

        return count

    def _filter_indicator(self, q_filters, s):
        if not q_filters.get('indicator'):
            return s

        i = q_filters.pop('indicator')

        try:
            itype = resolve_itype(i)
        except InvalidIndicator:
            s = s.query("match", message=i)
            return s

        if itype in ('email', 'url', 'fqdn'):
            s = s.filter('term', indicator=i)
            return s

        if itype is 'ipv4':
            ip = ipaddress.IPv4Network(i)
            mask = ip.prefixlen
            if mask < 8:
                raise InvalidSearch('prefix needs to be greater than or equal to 8')

            start = str(ip.network_address)
            end = str(ip.broadcast_address)

            s = s.filter('range', indicator_ipv4={'gte': start, 'lte': end})
            return s

        if itype is 'ipv6':
            ip = ipaddress.IPv6Network(i)
            mask = ip.prefixlen
            if mask < 32:
                raise InvalidSearch('prefix needs to be greater than or equal to 32')

            start = binascii.b2a_hex(socket.inet_pton(socket.AF_INET6, str(ip.network_address))).decode('utf-8')
            end = binascii.b2a_hex(socket.inet_pton(socket.AF_INET6, str(ip.broadcast_address))).decode('utf-8')

            s = s.filter('range', indicator_ipv6={'gte': start, 'lte': end})
            return s

    def _filter_terms(self, q_filters, s):
        for f in q_filters:
            kwargs = {f: q_filters[f]}
            if isinstance(q_filters[f], list):
                s = s.filter('terms', **kwargs)
            else:
                s = s.filter('term', **kwargs)

        return s

    def _filters_build(self, filters, s):

        q_filters = {}
        for f in VALID_FILTERS:
            if filters.get(f):
                q_filters[f] = filters[f]
        # treat indicator as special, transform into Search
        s = self._filter_indicator(q_filters, s)

        # transform all other filters into term=
        s = self._filter_terms(q_filters, s)

        logger.debug(s.to_dict())

        return s

    def indicators_search(self, filters, sort='reporttime', raw=False, timeout=TIMEOUT):
        limit = filters.get('limit', LIMIT)

        s = Indicator.search(index='indicators-*')
        s = s.params(size=limit, timeout=timeout, sort=sort)

        s = self._filters_build(filters, s)

        try:
            rv = s.execute()
        except elasticsearch.exceptions.RequestError as e:
            logger.error(e)
            return

        if not rv.hits.hits:
            return

        if raw:
            for r in rv.hits.hits:
                yield r

        for x in rv.hits.hits:
            yield x['_source']
