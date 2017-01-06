from elasticsearch_dsl import DocType, String, Date, Integer, Boolean, Float, Ip, GeoPoint
import elasticsearch.exceptions
from elasticsearch_dsl.connections import connections
import arrow
from pprint import pprint
import logging
from cif.constants import PYVERSION
from cif.store.token_plugin import TokenPlugin

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


class TokenMixin(TokenPlugin):

    def tokens_search(self, data, raw=False):
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
            if raw:
                yield x
            else:
                yield x['_source']

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

        d = list(self.tokens_search({'token': data['token']}))
        if not d:
            return 'token not found'

        d.update(fields=data)
        connections.get_connection().indices.flush(index='tokens')

    def token_update_last_activity_at(self, token, timestamp):
        timestamp = arrow.get(timestamp).datetime

        if self._token_cache_check(token):
            if self.token_cache[token].get('last_activity_at'):
                return self.token_cache[token]['last_activity_at']

            self.token_cache[token]['last_activity_at'] = timestamp
            return timestamp

        rv = list(self.tokens_search({'token': token}, raw=True))
        rv = Token.get(rv[0]['_id'])
        rv.update(last_activity_at=timestamp)

        self.token_cache[token] = rv.to_dict()
        self.token_cache[token]['last_activity_at'] = timestamp
