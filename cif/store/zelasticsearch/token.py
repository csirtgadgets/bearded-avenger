from elasticsearch_dsl import DocType, String, Date, Integer, Boolean, Float, Ip, GeoPoint
import elasticsearch.exceptions
from elasticsearch_dsl.connections import connections
import os

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


class TokenMixin(object):

    def tokens_admin_exists(self):
        s = Token.search()
        s.filter('term', admin=True)

        try:
            rv = s.execute()
        except elasticsearch.exceptions.NotFoundError:
            return False

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

        data['token'] = data['token']

        self.logger.debug(data)
        t = Token(**data)

        if t.save():
            connections.get_connection().indices.flush(index='tokens')
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

            connections.get_connection().indices.flush(index='tokens')
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
        connections.get_connection().indices.flush(index='tokens')

    def token_last_activity_at(self, token, timestamp=None):
        s = Token.search()
        s = s.filter('term', token=token.decode('utf-8'))
        rv = s.execute()
        if rv.hits.total > 0:
            rv = rv.hits.hits[0]
            rv = Token.get(rv['_id'])

            if timestamp:
                self.logger.debug('updating timestamp to: {}'.format(timestamp))
                rv.update(last_activity_at=timestamp)
                connections.get_connection().indices.flush(index='tokens')
                return timestamp
            else:
                return rv.last_activity_at
        else:
            return timestamp
