from elasticsearch_dsl import DocType, Date, Boolean, Keyword
import elasticsearch.exceptions
from elasticsearch_dsl.connections import connections
from elasticsearch import helpers
import arrow
import logging
from .constants import LIMIT, TIMEOUT, ReIndexError
from cif.constants import PYVERSION
from cif.store.token_plugin import TokenManagerPlugin
import os

logger = logging.getLogger('cif.store.zelasticsearch')

INDEX_NAME = 'tokens'
CONFLICT_RETRIES = os.getenv('CIF_STORE_ES_CONFLICT_RETRIES', 5)
CONFLICT_RETRIES = int(CONFLICT_RETRIES)


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
    last_edited_at = Date()
    last_edited_by = Keyword()
    created_at = Date()
    created_by = Keyword()

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
        s = s.params(size=LIMIT, timeout=TIMEOUT, version=True)

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
            token_dict = x['_source']
            token_dict['id'] = x['_id']
            token_dict['version'] = int(x['_version'])
            token_str = x['_source']['token']
            if token_str not in self._cache:
                logger.info('adding token {} to cache with data {}'.format(token_str, token_dict))
                self._cache[token_str] = token_dict

            if raw:
                yield x
            else:
                yield token_dict

    def auth_search(self, token):
        """Take in a dict token {'token': <token>} and return a list of dicts of token attribs containing:
            .id (str): unique db id of token record
            .token (str): the api token that was passed in
            .groups (list): list of groups for which the token is authorized
            .read (bool): present and True if token has read perms
            .write (bool): present and True if token has write perms
            .admin (bool): present and True if token has admin perms
            .last_activity_at (str): RFC3339 str present if token has had activity
        """
        # if token dict already cached, use that
        token_str = token['token']
        if self._cache_check(token_str):
            self._update_last_activity_at(token_str, arrow.utcnow().datetime)
            token_dict = self._cache[token_str]
            # wrap in a list as expected from output of this func
            return [token_dict]

        # otherwise do a fresh lookup
        rv = list(self.search(token))
        if rv and len(rv) == 1:
            # if successful auth, update token activity here rather than in store
            # if more than one result in list, could indicate wildcard attempt and no caching/updating should be done
            self._update_last_activity_at(token_str, arrow.utcnow().datetime)

        return rv

    def create(self, data, token={}):
        logger.debug(data)
        for v in ['admin', 'read', 'write']:
            if data.get(v):
                data[v] = True

        if data.get('token') is None:
            data['token'] = self._generate()

        data['created_at'] = arrow.utcnow().datetime.strftime('%Y-%m-%dT%H:%M:%SZ')
        data['created_by'] = token.get('username', token.get('token', 'unknown'))
        
        t = Token(**data)

        if t.save():
            connections.get_connection().indices.flush(index=INDEX_NAME)
            res = data
            res['id'] = t.to_dict(include_meta=True)['_id']
            return res

    def delete(self, data):
        if not (data.get('token') or data.get('username')):
            return 'username or token required'

        rv = list(self.search(data))

        if not rv:
            return 0

        for t in rv:
            if t['token'] in self._cache:
                self._cache.pop(t['token'])
            t = Token.get(t['id'])
            t.delete()

        connections.get_connection().indices.flush(index=INDEX_NAME)
        return len(rv)

    def edit(self, data, bulk=False, token={}):
        try:
            if bulk:
                dicts = []
                for token_str in data.keys():
                    token_dict = data[token_str]
                    _id = token_dict.pop('id') # don't want to save dict id back to es
                    _version = token_dict.pop('version') # don't want to save dict vers back to es

                    dicts.append({
                        '_op_type': 'update',
                        '_index': INDEX_NAME,
                        '_type': 'token',
                        '_id': _id,
                        '_version': _version,
                        '_body': {'doc': token_dict}
                    })
                helpers.bulk(connections.get_connection(), dicts)
            else:
                if not data.get('token'):
                    return 'token required for updating'

                token_str = data['token']

                d = list(self.search({'token': token_str}))
                if not d:
                    logger.error('token update: token not found')
                    return 'token not found'

                t = d[0]

                data['last_edited_at'] = arrow.utcnow().datetime.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
                data['last_edited_by'] = token.get('username', token.get('token', 'unknown'))

                t.update(data)
                logger.debug('Updating token with info {}'.format(t))
                self._cache[token_str] = t
                logger.debug('Cached token info now {}'.format(self._cache[token_str]))
                self._flush_cache(force=True)

        except elasticsearch.exceptions.TransportError as e:
            if e.status_code == 409:
                logger.warn('Token doc updated by something else: {}'.format(e.error))
            elif e.status_code == 404:
                logger.warn('Token doc missing/removed by another process: {}'.format(e.error))
            else:
                logger.error('Token update TransportError: {}'.format(e.error))

        except helpers.BulkIndexError as e:
            for err in e.errors:
                if err.get('update', {}).get('status', 9999) == 409:
                    # version conflict error, prob just modified by another mp processs
                    logger.warn('Token doc updated by something else: {}'.format(err))
                elif err.get('update', {}).get('status', 9999) == 404:
                    # doc missing error, token prob deleted while another router host still had it cached
                    logger.warn('Token doc missing/removed by another process: {}'.format(err))
                else:
                    import traceback
                    logger.error('Token update exception: {}'.format(err))
                    logger.error(traceback.print_exc())

        except Exception as e:
            import traceback
            logger.error('Token update exception: {}'.format(e))
            logger.error(traceback.print_exc())
            return False

        connections.get_connection().indices.flush(index=INDEX_NAME)
        return True
