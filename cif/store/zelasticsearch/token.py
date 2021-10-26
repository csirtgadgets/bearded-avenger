from elasticsearch_dsl import DocType, String, Date, Integer, Boolean, Float, Ip, GeoPoint, Keyword, Index
import elasticsearch.exceptions
from elasticsearch_dsl.connections import connections
import arrow
from pprint import pprint
import logging
from .constants import LIMIT, TIMEOUT
from cif.constants import PYVERSION
from cif.store.token_plugin import TokenManagerPlugin
import os

logger = logging.getLogger('cif.store.zelasticsearch')

INDEX_NAME = 'tokens'
CONFLICT_RETRIES = os.getenv('CIF_STORE_ES_CONFLICT_RETRIES', 5)
CONFLICT_RETRIES = int(CONFLICT_RETRIES)


class ReIndexError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class Token(DocType):
    username = Keyword()
    token = Keyword()
    expires = Date()
    read = Boolean()
    write = Boolean()
    revoked = Boolean()
    acl = Keyword()
    groups = Keyword()
    admin = Boolean()
    last_activity_at = Date()

    class Meta:
        index = INDEX_NAME


class TokenManager(TokenManagerPlugin):
    def __init__(self, *args, **kwargs):
        try:
            Token.init()
        except elasticsearch.exceptions.RequestError:
            raise ReIndexError("Your Tokens index is using an old mapping, please run reindex_tokens.py")
        except Exception as e:
            raise ReIndexError("Unspecified error: %s" % e)

        super(TokenManager, self).__init__(**kwargs)

    def search(self, data, raw=False):
        s = Token.search()
        s = s.params(size=LIMIT, timeout=TIMEOUT)

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

    def auth_search(self, token):
        """Take in a str token and return a dict of token attribs containing:
            .id (str): unique db id of token record
            .token (str): the api token that was passed in
            .groups (list): list of groups for which the token is authorized
            .read (bool): present and True if token has read perms
            .write (bool): present and True if token has write perms
            .admin (bool): present and True if token has admin perms
            .last_activity_at (str): RFC3339 str present if token has had activity
        """
        rv = list(self.search(token, raw=True))
        final = []
        # standardize all token dicts to contain an "id" field w/ the id of the record
        for x in rv:
            y = x['_source']
            y['id'] = x['_id']
            final.append(y)
        if final:
            # if successful auth, update token activity here rather than in store
            self.update_last_activity_at(final[0], arrow.utcnow().datetime)
        return final

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
            res = t.to_dict()
            res['id'] = t.to_dict(include_meta=True)['_id']
            return res

    def delete(self, data):
        if not (data.get('token') or data.get('username')):
            return 'username or token required'

        rv = list(self.search(data, raw=True))

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

        d = list(self.search({'token': data['token']}, raw=True))
        if not d:
            logger.error('token update: unknown token')
            return 'token not found'

        t = d[0]['_source']
        d = Token.get(d[0]['_id'])

        for f in data:
            t[f] = data[f]

        try:
            d.update(**t)

        except Exception as e:
            import traceback
            logger.error(traceback.print_exc())
            return False

        connections.get_connection().indices.flush(index='tokens')
        return True

    def update_last_activity_at(self, token, timestamp):
        if isinstance(timestamp, str):
            timestamp = arrow.get(timestamp).datetime

        timestamp = timestamp.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        token_str = token['token']
        if self._cache_check(token_str):

            if self._cache[token_str].get('last_activity_at'):
                return self._cache[token_str]['last_activity_at']

            self._cache[token_str]['last_activity_at'] = timestamp
            return timestamp

        rv = Token.get(token['id'])

        try:
            rv.update(last_activity_at=timestamp, retry_on_conflict=CONFLICT_RETRIES)
            self._cache[token_str] = rv.to_dict()
            self._cache[token_str]['last_activity_at'] = timestamp
        except Exception as e:
            import traceback
            logger.error(traceback.print_exc())

        return timestamp
