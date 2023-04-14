import arrow
from cif.constants import TOKEN_CACHE_DELAY, TOKEN_LENGTH
from cif.utils import strtobool
from cifsdk.exceptions import AuthError
import os
import binascii
import abc
import logging
from datetime import datetime

TRACE = strtobool(os.environ.get('CIF_TOKEN_TRACE', False))

logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)

if TRACE:
    logger.setLevel(logging.DEBUG)

class TokenManagerPlugin(object):
    __metaclass__ = abc.ABCMeta

    def __init__(self, *args, **kwargs):
        self._cache = kwargs.get('token_cache', {})
        self._cache_check_next = arrow.utcnow().int_timestamp + TOKEN_CACHE_DELAY

    @abc.abstractmethod
    def create(self, data):
        raise NotImplementedError

    @abc.abstractmethod
    def delete(self, data):
        raise NotImplementedError

    @abc.abstractmethod
    def search(self, data):
        raise NotImplementedError

    @abc.abstractmethod
    def auth_search(self, token):
        raise NotImplementedError

    @abc.abstractmethod
    def edit(self, data, bulk=False, token=None):
        raise NotImplementedError

    def _update_token_cache_field(self, token_str, field, new_value):
        # since self._cache is a mp.Manager.dict, directly updating a nested dict inside
        # won't propagate. need to re-assign modified nested dict
        # https://docs.python.org/3.8/library/multiprocessing.html#proxy-objects
        token_dict = self._cache[token_str]
        token_dict[field] = new_value
        self._cache[token_str] = token_dict

    def _update_last_activity_at(self, token_str, timestamp):
        # internal method and should only be called by auth_search
        # takes in a token str and timestamp as datetime obj
        timestamp = timestamp.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        # update the cache where it will be flushed later
        self._update_token_cache_field(token_str, 'last_activity_at', timestamp)

    def _generate(self):
        return binascii.b2a_hex(os.urandom(TOKEN_LENGTH)).decode('utf-8')

    def _flush_cache(self, force=False):
        if force or arrow.utcnow().int_timestamp > self._cache_check_next:
            logger.debug('flushing token cache...')
            # write cache back to store, where _cache is a dict of dicts with token_strs as keys
            self.edit(self._cache, bulk=True)
            self._cache.clear()
            self._cache_check_next = arrow.utcnow().int_timestamp + TOKEN_CACHE_DELAY

            logger.debug('token cache flushed..')

    def _cache_check(self, token_str, k=None):
        self._flush_cache()
        if token_str not in self._cache:
            return False

        return self._cache[token_str]

    def admin_exists(self):
        t = list(self.search({'admin': True}))
        if len(t) > 0:
            return t[0]['token']

    def hunter_exists(self):
        t = list(self.search({'username': 'hunter'}))
        if len(t) > 0:
            return t[0]

    def check(self, token, k, v=True):
        self._flush_cache()
        token_str = token['token']
        if token_str in self._cache and self._cache[token_str].get(k):
            return self._cache[token_str]

        rv = list(self.search({'token': token_str, k: v}))
        if len(rv) == 0:
            raise AuthError('unauthorized')

        self._cache[token_str] = rv[0]
        return rv[0]

    def admin(self, token):
        return self.check(token, 'admin')

    def read(self, token):
        return self.check(token, 'read')

    def write(self, token):
        return self.check(token, 'write')

    def last_activity_at(self, token):
        token_str = token['token']
        if self._cache.get(token_str, {}).get('last_activity_at'):
            rv = self._cache[token_str]['last_activity_at']
        else:
            rv = list(self.search({'token': token_str}))

            if not rv:
                return None

            rv = rv[0].get('last_activity_at', None)

        if isinstance(rv, datetime):
            # return RFC3339 formatted str instead of datetime
            rv = rv.strftime('%Y-%m-%dT%H:%M:%S.%fZ')

        return rv
