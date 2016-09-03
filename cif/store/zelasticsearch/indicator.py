from elasticsearch_dsl import DocType, String, Date, Integer, Float, Ip, Mapping, Index, GeoPoint

import elasticsearch.exceptions
from elasticsearch_dsl.connections import connections
import os
from pprint import pprint
from cifsdk.exceptions import AuthError, InvalidSearch
from csirtg_indicator import resolve_itype
from datetime import datetime
import ipaddress
import arrow
ES_NODES = os.getenv('CIF_ES_NODES', '127.0.0.1:9200')
VALID_FILTERS = ['indicator', 'confidence', 'provider', 'itype', 'group']

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
    group = String(multi=True, index="not_analyzed")
    itype = String(index="not_analyzed")
    tlp = String(index="not_analyzed")
    provider = String(index="not_analyzed")
    portlist = String()
    asn = Float()
    asn_desc = String()
    cc = String()
    protocol = String()
    reporttime = Date()
    lasttime = Date()
    firsttime = Date()
    confidence = Integer()
    timezone = String()
    city = String()
    description = String(index="not_analyzed")
    additional_data = String(multi=True)
    tags = String(multi=True)
    rdata = String(index="not_analyzed")
    msg = String()
    count = Integer()


class _Indicator(object):
    def _dict(self, data):
        return [x.__dict__['_d_'] for x in data.hits]

    def _current_index(self):
        dt = datetime.utcnow()
        dt = dt.strftime('%Y.%m')
        return dt

    def _create_index(self):
        # https://github.com/csirtgadgets/massive-octo-spice/blob/develop/elasticsearch/observables.json
        # http://elasticsearch-py.readthedocs.org/en/master/api.html#elasticsearch.Elasticsearch.bulk
        dt = self._current_index()
        es = connections.get_connection()
        if not es.indices.exists('indicators-{}'.format(dt)):
            index = Index('indicators-{}'.format(dt))
            index.aliases(live={})
            index.doc_type(Indicator)
            index.create()

            m = Mapping('indicator')
            m.field('indicator_ipv4', 'ip')
            m.field('indicator_ipv4_mask', 'integer')
            m.field('lasttime', 'date')
            m.save('indicators-{}'.format(dt))
        return 'indicators-{}'.format(dt)

    def indicators_create(self, token, data):
        index = self._create_index()

        self.logger.debug('index: {}'.format(index))
        data['meta'] = {}
        data['meta']['index'] = index

        if resolve_itype(data['indicator']) == 'ipv4':
            import re
            match = re.search('^(\S+)\/(\d+)$', data['indicator'])
            if match:
                data['indicator_ipv4'] = match.group(1)
                data['indicator_ipv4_mask'] = match.group(2)
            else:
                data['indicator_ipv4'] = data['indicator']

        if type(data['group']) != list:
            data['group'] = [data['group']]

        self.logger.debug(data)
        i = Indicator(**data)
        self.logger.debug(i)
        if i.save():
            return i.__dict__['_d_']
        else:
            raise AuthError('invalid token')

    def indicators_upsert(self, token, data):
        if not self.token_write(token):
            raise AuthError('invalid token')

        index = self._create_index()

        if isinstance(data, dict):
            data = [data]

        n = 0
        tmp = {}  # to deal with es flushing

        es = connections.get_connection()

        # TODO -- bulk mode
        for d in data:

            filters = {
                'indicator': d['indicator'],
                'provider': d['provider']
            }

            # TODO -- make sure the initial list is sorted first (by lasttime)
            rv = self.indicators_search(token, filters, sort='-lasttime', raw=True)

            # if we have results
            if len(rv) > 0:
                r = rv[0]

                self.logger.debug(r)
                # if it's a newer result
                if arrow.get(d['lasttime']).datetime > arrow.get(r['_source']['lasttime']).datetime:
                    # carry the index'd data forward and remove the old index
                    i = es.get(index=r['_index'], id=r['_id'])
                    i['_source']['count'] += 1
                    meta = es.update(index=r['_index'], doc_type='indicator', id=r['_id'], body={'doc': i['_source']})
            else:
                if tmp.get(d['indicator']):
                    if d['lasttime'] in tmp[d['indicator']]:
                        self.logger.debug('skipping: %s' % d['indicator'])
                        continue
                else:
                    tmp[d['indicator']] = set()

                d['count'] = 1
                if not d.get('firsttime'):
                    d['firsttime'] = arrow.utcnow().datetime

                rv = self.indicators_create(token, d)
                es.indices.flush(index='indicators-{}'.format(self._current_index()))
                if rv:
                    n += 1
                    tmp[d['indicator']].add(d['lasttime'])

                pprint(tmp)
                pprint(d)

        return n

    def indicators_search(self, token, filters, sort=None, raw=False):
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
            itype = resolve_itype(q_filters['indicator'])

            if itype == 'ipv4':
                ip = ipaddress.IPv4Network(q_filters['indicator'])
                mask = ip.prefixlen
                if mask < 8:
                    raise InvalidSearch('prefix needs to be greater than or equal to 8')
                start = str(ip.network_address)
                end = str(ip.broadcast_address)

                s = s.filter('range', indicator_ipv4={'gte': start, 'lte': end})
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
                return [x['_source'] for x in rv.hits.hits]
            except KeyError:
                return []