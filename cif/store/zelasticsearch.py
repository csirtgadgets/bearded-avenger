from elasticsearch_dsl import Search, DocType, String, Date, Integer, Boolean, Float, Ip, Mapping, Index, Nested, GeoPoint

import elasticsearch.exceptions
from elasticsearch_dsl.connections import connections
import os
import logging
from pprint import pprint
from cifsdk.exceptions import AuthError, InvalidSearch
from csirtg_indicator import resolve_itype
from datetime import datetime
import ipaddress

from cif.store.plugin import Store
ES_NODES = os.getenv('CIF_ES_NODES', '127.0.0.1:9200')
VALID_FILTERS = ['indicator', 'confidence', 'provider', 'itype', 'group']

LIMIT = 5000
LIMIT = os.getenv('CIF_ES_LIMIT', LIMIT)

LIMIT_HARD = 500000
LIMIT_HARD = os.getenv('CIF_ES_LIMIT_HARD', LIMIT_HARD)

TIMEOUT = '120'
TIMEOUT = os.getenv('CIF_ES_TIMEOUT', TIMEOUT)
TIMEOUT = '{}s'.format(TIMEOUT)


class Token(DocType):
    username = String()
    token = String()
    expires = Date()
    read = Boolean()
    write = Boolean()
    revoked = Boolean()
    acl = String()
    groups = String()
    admin = Boolean()
    last_activity_at = Date()

    class Meta:
        index = 'tokens'


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

    # set on insert
    #class Meta:
    #    index = 'indicators'


class ElasticSearch_(Store):

    name = 'elasticsearch'

    def __init__(self, nodes=ES_NODES):
        self.logger = logging.getLogger(__name__)

        if type(nodes) == str:
            nodes = nodes.split(',')

        self.logger.info('setting es nodes {}'.format(nodes))
        connections.create_connection(hosts=nodes)

    def _dict(self, data):
        return [x.__dict__['_d_'] for x in data.hits]

    def _create_index(self):
        # https://github.com/csirtgadgets/massive-octo-spice/blob/develop/elasticsearch/observables.json
        # http://elasticsearch-py.readthedocs.org/en/master/api.html#elasticsearch.Elasticsearch.bulk
        dt = datetime.utcnow()
        dt = dt.strftime('%Y.%m')
        es = connections.get_connection()
        if not es.indices.exists('indicators-{}'.format(dt)):
            index = Index('indicators-{}'.format(dt))
            index.aliases(live={})
            index.doc_type(Indicator)
            index.create()

            m = Mapping('indicator')
            m.field('indicator_ipv4', 'ip')
            m.field('indicator_ipv4_mask', 'integer')
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

    def indicators_search(self, token, filters):
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

        s = Indicator.search()
        s = s.params(size=limit, timeout=timeout)
        s = s.sort('-reporttime')

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

        try:
            return [x['_source'] for x in rv.hits.hits]
        except KeyError:
            return []

    def ping(self, token):
        # http://elasticsearch-py.readthedocs.org/en/master/api.html#elasticsearch.client.IndicesClient.stats
        x = connections.get_connection().cluster.health()
        if x['status'] != 'red':
            return True

    def tokens_admin_exists(self):
        s = Token.search()
        s.filter('term', admin=True)

        try:
            rv = s.execute()
        except elasticsearch.exceptions.NotFoundError:
            return False

        #self.logger.warn(rv.to_dict())
        if rv.hits.total > 0:
            return True

        return False

    def tokens_create(self, data):
        self.logger.debug(data)
        if data.get('admin'):
            data['admin'] = True

        if data.get('read'):
            data['read'] = True

        if data.get('write'):
            data['write'] = True

        if not data.get('token'):
            data['token'] = self._token_generate()

        self.logger.debug(data)
        t = Token(**data)

        if t.save():
            return t.__dict__['_d_']

    def tokens_delete(self, data):
        if not (data.get('token') or data.get('username')):
            return 'username or token required'

        s = Token.search()

        if data.get('username'):
            s = s.filter('term', username=data['username'])

        if data.get('token'):
            s = s.filter('term', token=data['token'])

        rv = s.execute()

        if rv.hits.total > 0:
            for t in rv.hits.hits:
                t = Token.get(t['_id'])
                t.delete()

            return rv.hits.total
        else:
            return 0

    def tokens_search(self, data):
        s = Token.search()

        if data.get('token'):
            s = s.filter('term', token=data['token'])

        if data.get('username'):
            s = s.filter('term', username=data['username'])

        rv = s.execute()

        return [x['_source'] for x in rv.hits.hits]

    def token_admin(self, token):
        s = Token.search()

        s = s.filter('term', token=token)
        s = s.filter('term', admin=True)

        rv = s.execute()

        if rv.hits.total > 0:
            return True

    def token_read(self, token):
        s = Token.search()

        s = s.filter('term', token=token)
        s = s.filter('term', read=True)
        rv = s.execute()

        if rv.hits.total > 0:
            return True

        return False

    def token_write(self, token):
        s = Token.search()

        s = s.filter('term', token=token)
        s = s.filter('term', write=True)
        rv = s.execute()

        if rv.hits.total > 0:
            return True

        return False

    def token_edit(self, data):
        if not data.get('token'):
            return 'token required for updating'

        s = Token.search()

        s = s.filter('term', token=data['token'])
        rv = s.execute()

        if not rv.hits.total > 0:
            return 'token not found'

        d = rv.hits.hits[0]
        d.update(fields=data)

    def token_last_activity_at(self, token, timestamp=None):
        s = Token.search()
        s = s.filter('term', token=token)
        rv = s.execute()
        rv = rv.hits.hits[0]
        rv = Token.get(rv['_id'])

        if timestamp:
            self.logger.debug('updating timestamp to: {}'.format(timestamp))
            rv.update(last_activity_at=timestamp)
            return timestamp
        else:
            return rv.last_activity_at

Plugin = ElasticSearch_

