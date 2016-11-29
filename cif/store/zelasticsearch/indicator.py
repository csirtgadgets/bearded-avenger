from elasticsearch_dsl import DocType, String, Date, Integer, Float, Ip, Mapping, Index, GeoPoint, Byte

import elasticsearch.exceptions
from elasticsearch_dsl.connections import connections
import os
from pprint import pprint
from cifsdk.exceptions import AuthError, InvalidSearch
from csirtg_indicator import resolve_itype
from csirtg_indicator.exceptions import InvalidIndicator
from cifsdk.constants import PYVERSION
from datetime import datetime
import ipaddress
import arrow
import re
from base64 import b64decode, b64encode
import binascii
import socket

VALID_FILTERS = ['indicator', 'confidence', 'provider', 'itype', 'group', 'tags']

LIMIT = 5000
LIMIT = os.getenv('CIF_ES_LIMIT', LIMIT)

LIMIT_HARD = 500000
LIMIT_HARD = os.getenv('CIF_ES_LIMIT_HARD', LIMIT_HARD)

TIMEOUT = '120'
TIMEOUT = os.getenv('CIF_ES_TIMEOUT', TIMEOUT)
TIMEOUT = '{}s'.format(TIMEOUT)


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


# def _dict(data):
#     return [x.__dict__['_d_'] for x in data.hits]


class IndicatorMixin(object):

    def indicators_create(self, data, raw=False):
        index = _create_index()

        self.logger.debug('index: {}'.format(index))
        data['meta'] = {}
        data['meta']['index'] = index

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

                data['indicator_ipv6'] = binascii.b2a_hex(socket.inet_pton(socket.AF_INET6, match.group(1))).decode('utf-8')
                data['indicator_ipv6_mask'] = match.group(2)
            else:
                data['indicator_ipv6'] = binascii.b2a_hex(socket.inet_pton(socket.AF_INET6, data['indicator'])).decode('utf-8')

        if type(data['group']) != list:
            data['group'] = [data['group']]

        if data.get('message'):
            try:
                data['message'] = str(b64decode(data['message']))
            except (TypeError, binascii.Error) as e:
                pass

        i = Indicator(**data)

        if i.save():
            if raw:
                return i
            else:
                return i.__dict__['_d_']
        else:
            raise AuthError('invalid token')

    def indicators_upsert(self, data):
        index = _create_index()

        if isinstance(data, dict):
            data = [data]

        n = 0
        tmp = {}  # to deal with es flushing

        es = connections.get_connection()

        # TODO -- bulk mode
        for d in data:

            filters = {
                'indicator': d['indicator'],
                'provider': d['provider'],
            }

            if d.get('tags'):
                filters['tags'] = d['tags']

            # TODO -- make sure the initial list is sorted first (by lasttime)
            rv = self.indicators_search(filters, sort='lasttime', raw=True)

            # if we have results
            if len(rv) > 0:
                r = rv[0]

                # if it's a newer result
                if d['lasttime'] and (arrow.get(d['lasttime']).datetime > arrow.get(r['_source']['lasttime']).datetime):
                    # carry the index'd data forward and remove the old index
                    i = es.get(index=r['_index'], doc_type='indicator', id=r['_id'])
                    if r['_index'] == _current_index():
                        i['_source']['count'] += 1
                        i['_source']['lasttime'] = d['lasttime']
                        i['_source']['reporttime'] = d['reporttime']
                        if d.get('message'):
                            if not i['_source'].get('message'):
                                i['_source']['message'] = []
                            i['_source']['message'].append(d['message'])

                        meta = es.update(index=r['_index'], doc_type='indicator', id=r['_id'], body={'doc': i['_source']})
                    else:
                        # carry the information forward
                        d['count'] = i['_source']['count'] + 1
                        i['_source']['lasttime'] = d['lasttime']
                        i['_source']['reporttime'] = d['reporttime']
                        if d.get('message'):
                            if not i['_source'].get('message'):
                                i['_source']['message'] = []
                            i['_source']['message'].append(d['message'])
                        self.indicators_create(d)
                        es.delete(index=r['_index'], doc_type='indicator', id=r['_id'], refresh=True)

                    es.indices.flush(index=_current_index())

                # else do nothing, it's prob a duplicate
            else:
                if tmp.get(d['indicator']):
                    if d['lasttime'] in tmp[d['indicator']]:
                        self.logger.debug('skipping: %s' % d['indicator'])
                        continue
                else:
                    tmp[d['indicator']] = set()

                d['count'] = 1

                if not d.get('lasttime'):
                    d['lasttime'] = arrow.utcnow().datetime

                if not d.get('firsttime'):
                    d['firsttime'] = d['lasttime']

                rv = self.indicators_create(d)
                es.indices.flush(index=_current_index())

                if rv:
                    n += 1
                    tmp[d['indicator']].add(d['lasttime'])

        return n

    def indicators_search(self, filters, sort=None, raw=False):
        # build filters with elasticsearch-dsl
        # http://elasticsearch-dsl.readthedocs.org/en/latest/search_dsl.html

        limit = filters.get('limit')
        if limit:
            del filters['limit']
        else:
            limit = LIMIT

        nolog = filters.get('nolog')
        if nolog:
            del filters['nolog']

        timeout = TIMEOUT

        s = Indicator.search(index='indicators-*')
        s = s.params(size=limit, timeout=timeout)
        if sort:
            s = s.sort(sort)

        q_filters = {}
        for f in VALID_FILTERS:
            if filters.get(f):
                q_filters[f] = filters[f]

        if q_filters.get('indicator'):
            try:
                itype = resolve_itype(q_filters['indicator'])

                if itype == 'ipv4':
                    if PYVERSION == 2:
                        q_filters['indicator'] = unicode(q_filters['indicator'])

                    ip = ipaddress.IPv4Network(q_filters['indicator'])
                    mask = ip.prefixlen
                    if mask < 8:
                        raise InvalidSearch('prefix needs to be greater than or equal to 8')
                    start = str(ip.network_address)
                    end = str(ip.broadcast_address)

                    s = s.filter('range', indicator_ipv4={'gte': start, 'lte': end})
                elif itype is 'ipv6':
                    if PYVERSION == 2:
                        q_filters['indicator'] = unicode(q_filters['indicator'])

                    ip = ipaddress.IPv6Network(q_filters['indicator'])
                    mask = ip.prefixlen
                    if mask < 32:
                        raise InvalidSearch('prefix needs to be greater than or equal to 32')

                    start = binascii.b2a_hex(socket.inet_pton(socket.AF_INET6, str(ip.network_address))).decode('utf-8')
                    end = binascii.b2a_hex(socket.inet_pton(socket.AF_INET6, str(ip.broadcast_address))).decode('utf-8')

                    s = s.filter('range', indicator_ipv6={'gte': start, 'lte': end})

                elif itype in ('email', 'url', 'fqdn'):
                    s = s.filter('term', indicator=q_filters['indicator'])

            except InvalidIndicator:
                s = s.query("match", message=q_filters['indicator'])

            del q_filters['indicator']

        for f in q_filters:
            kwargs = {f: q_filters[f]}
            s = s.filter('term', **kwargs)

        try:
            rv = s.execute()
        except elasticsearch.exceptions.RequestError as e:
            self.logger.error(e)
            return []

        if raw:
            try:
                return rv.hits.hits
            except KeyError:
                return []
        else:
            try:
                data = []
                for x in rv.hits.hits:
                    if x['_source'].get('message'):
                        x['_source']['message'] = b64encode(x['_source']['message'].encode('utf-8'))
                    data.append(x['_source'])
                return data
            except KeyError as e:
                self.logger.error(e)
                return []
