from elasticsearch import Elasticsearch
from elasticsearch_dsl import Search, DocType, String, Date, Integer, Boolean, Float, Ip, Mapping

import elasticsearch.exceptions
from elasticsearch_dsl.connections import connections
import os
import logging
from pprint import pprint
import arrow
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
    indicator = String()
    indicator_ipv4 = Ip()
    group = String()
    itype = String()
    tlp = String()
    provider = String()
    portlist = String()
    asn = Float()
    asn_desc = String()
    cc = String()
    protocol = Integer()
    reporttime = Date()
    lasttime = Date()
    firsttime = Date()
    confidence = Integer
    timezone = String()
    city = String()
    peers = String()
    description = String()
    additional_data = String()

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
        #self.handle = Elasticsearch(nodes)
        connections.create_connection(hosts=nodes)

        m = Mapping('indicator')
        m.field('indicator_ipv4', 'ip')
        m.field('indicator_ipv4_mask', 'integer')
        m.field('reporttime', 'date')
        m.save('indicators-2016.06')

    def _dict(self, data):
        return [x.__dict__['_d_'] for x in data.hits]

    def indicators_create(self, token, data):
        # http://elasticsearch-py.readthedocs.org/en/master/api.html#elasticsearch.Elasticsearch.bulk
        dt = datetime.utcnow()
        dt = dt.strftime('%Y.%m')
        index = 'indicators-{}'.format(dt)

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
        timeout = '{}s'.format(timeout)

        s = Indicator.search()
        s = s.params(size=limit, timeout=timeout, filter_path=['hits.hits._source', 'hits.hits._type'])
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
        s = Search(using=connections.get_connection(), index='cif-tokens') \
                .filter("term", admin='True')

        response = []
        try:
            response = s.execute()
        except elasticsearch.exceptions.NotFoundError:
            return False

        return True

    def tokens_create(self, data):
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
            rv = t.__dict__['_d_']
            return rv

    def tokens_delete(self, data):
        return True

    def tokens_search(self, data):
        s = Token.search()

        if data.get('token'):
            s.filter('term', token=data['token'])

        if data.get('username'):
            s.filter('term', username=data['username'])

        rv = s.execute()

        return self._dict(rv)

    def token_admin(self, token):
        return True

    def token_read(self, token):
        return True

    def token_write(self, token):
        return True

    def token_edit(self, data):
        return True

    def token_last_activity_at(self, token, timestamp=None):
        if timestamp:
            s = Token.search()
            s = s.filter('term', token=token)
            r = s.execute()

        return arrow.utcnow()

Plugin = ElasticSearch_

