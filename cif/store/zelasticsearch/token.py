from elasticsearch_dsl import DocType, String, Date, Integer, Boolean, Float, Ip, GeoPoint
import elasticsearch.exceptions
from elasticsearch_dsl.connections import connections
import os
from cif.constants import TOKEN_CACHE_DELAY
import arrow
from pprint import pprint
import logging

logger = logging.getLogger('cif.store.zelasticsearch')

INDEX_NAME = 'tokens'


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


class TokenMixin(object):

    def _token_flush_cache(self):
        if arrow.utcnow().timestamp > self.token_cache_check:
            self.token_cache = {}
            self.token_cache_check = arrow.utcnow().timestamp + TOKEN_CACHE_DELAY

    def tokens_search(self, data, raw=False):
        s = Token.search()

        for k in ['token', 'username', 'admin', 'write', 'read']:
            if data.get(k):
                s = s.filter('term', **{k: data[k]})

        try:
            rv = s.execute()
        except elasticsearch.exceptions.NotFoundError as e:
            logger.error(e)
            return False

        if rv.hits.total == 0:
            return None

        if raw:
            return rv.hits.hits

        return [x['_source'] for x in rv.hits.hits]

    def tokens_admin_exists(self):
        return self.tokens_search({'admin': True})

    def token_check(self, token, k, v=True):
        if token in self.token_cache and self.token_cache[token].get(k):
            return self.token_cache[token]

        return self.tokens_search({'token': token, k: v})

    def token_admin(self, token):
        self._token_flush_cache()
        return self.token_check(token, 'admin')

    def token_read(self, token):
        return self.token_check(token, 'read')

    def token_write(self, token):
        return self.token_check(token, 'write')

    def tokens_create(self, data):
        logger.debug(data)
        for v in ['admin', 'read', 'write']:
            if data.get(v):
                data[v] = True

        if not data.get('token'):
            data['token'] = self._token_generate()

        t = Token(**data)

        if t.save():
            connections.get_connection().indices.flush(index='tokens')
            return t.to_dict()

    def tokens_delete(self, data):
        if not (data.get('token') or data.get('username')):
            return 'username or token required'

        rv = self.tokens_search(data, raw=True)

        if not rv:
            return 0

        for t in rv:
            t = Token.get(t['_id'])
            t.delete()

        connections.get_connection().indices.flush(index='tokens')
        return len(rv)

    def token_edit(self, data):
        if not data.get('token'):
            return 'token required for updating'

        d = self.tokens_search({'token': data['token']})
        if not d:
            return 'token not found'

        d.update(fields=data)
        connections.get_connection().indices.flush(index='tokens')

    def token_last_activity_at(self, token, timestamp=None):

        timestamp = arrow.get(timestamp).datetime
        token = token.decode('utf-8')

        if not timestamp:
            if token in self.token_cache and self.token_cache[token].get('last_activity_at'):
                return self.token_cache[token]['last_activity_at']

            rv = self.tokens_search({'token': token})
            if not rv:
                return None

            return rv['last_activity_at']

        rv = self.tokens_search({'token': token}, raw=True)
        rv = Token.get(rv[0]['_id'])

        logger.debug('updating timestamp to: {}'.format(timestamp))
        rv.update(last_activity_at=timestamp)

        if token not in self.token_cache:
            self.token_cache[token] = {}

        self.token_cache[token]['last_activity_at'] = timestamp
