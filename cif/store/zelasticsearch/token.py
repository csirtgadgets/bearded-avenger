from elasticsearch_dsl import DocType, String, Date, Integer, Boolean, Float, Ip, GeoPoint
import elasticsearch.exceptions
from elasticsearch_dsl.connections import connections
import arrow
from pprint import pprint
import logging
from cif.constants import PYVERSION
from cif.store.token_plugin import TokenManagerPlugin
import os

logger = logging.getLogger('cif.store.zelasticsearch')

INDEX_NAME = 'tokens'
CONFLICT_RETRIES = os.getenv('CIF_STORE_ES_CONFLICT_RETRIES', 5)
CONFLICT_RETRIES = int(CONFLICT_RETRIES)


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
        index = INDEX_NAME


class TokenManager(TokenManagerPlugin):
    def __init__(self, *args, **kwargs):
        super(TokenManager, self).__init__(**kwargs)

    def search(self, data, raw=False):
        s = Token.search()

        for k in ['token', 'username', 'admin', 'write', 'read']:
            if data.get(k):
                if PYVERSION == 3:
                    if isinstance(data[k], bytes):
                        data[k] = data[k].decode('utf-8')

                s = s.filter('term', **{k: data[k]})

        try:
            rv = s.execute()
        except elasticsearch.exceptions.NotFoundError as e:
            logger.error(e)
            return

        if rv.hits.total == 0:
            return

        for x in rv.hits.hits:
            # update cache
            if x['_source']['token'] not in self._cache:
                self._cache[x['_source']['token']] = x['_source']

            if raw:
                yield x
            else:
                yield x['_source']

    def create(self, data):
        logger.debug(data)
        for v in ['admin', 'read', 'write']:
            if data.get(v):
                data[v] = True

        if data.get('token') is None:
            data['token'] = self._generate()

        t = Token(**data)

        if t.save():
            connections.get_connection().indices.flush(index='tokens')
            return t.to_dict()

    def delete(self, data):
        if not (data.get('token') or data.get('username')):
            return 'username or token required'

        rv = self.search(data, raw=True)

        if not rv:
            return 0

        for t in rv:
            t = Token.get(t['_id'])
            t.delete()

        connections.get_connection().indices.flush(index='tokens')
        return len(rv)

    def edit(self, data):
        if not data.get('token'):
            return 'token required for updating'

        d = list(self.search({'token': data['token']}))
        if not d:
            return 'token not found'

        d.update(fields=data)
        connections.get_connection().indices.flush(index='tokens')

    def update_last_activity_at(self, token, timestamp):
        if isinstance(timestamp, str):
            timestamp = arrow.get(timestamp).datetime

        if self._cache_check(token):

            if self._cache[token].get('last_activity_at'):
                return self._cache[token]['last_activity_at']

            self._cache[token]['last_activity_at'] = timestamp
            return timestamp

        rv = list(self.search({'token': token}, raw=True))
        rv = Token.get(rv[0]['_id'])

        try:
            rv.update(last_activity_at=timestamp, retry_on_conflict=5)
        except Exception as e:
            import traceback
            logger.error(traceback.print_exc())

        self._cache[token] = rv.to_dict()
        self._cache[token]['last_activity_at'] = timestamp
        return timestamp
