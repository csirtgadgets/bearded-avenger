import arrow
from cif.constants import TOKEN_CACHE_DELAY, TOKEN_LENGTH
from cifsdk.exceptions import AuthError
import os
import binascii
import abc


class TokenManagerPlugin(object):
    __metaclass__ = abc.ABCMeta

    def __init__(self, *args, **kwargs):
        self._cache = {}
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
    def edit(self, data):
        raise NotImplementedError

    @abc.abstractmethod
    def update_last_activity_at(self, timestamp):
        raise NotImplementedError

    def _generate(self):
        return binascii.b2a_hex(os.urandom(TOKEN_LENGTH)).decode('utf-8')

    def _flush_cache(self):
        if arrow.utcnow().int_timestamp > self._cache_check_next:
            self._cache = {}
            self._cache_check_next = arrow.utcnow().int_timestamp + TOKEN_CACHE_DELAY

    def _cache_check(self, token, k=None):
        self._flush_cache()
        if token not in self._cache:
            return False

        return self._cache[token]

    def admin_exists(self):
        t = list(self.search({'admin': True}))
        if len(t) > 0:
            return t[0]['token']

    def check(self, token, k, v=True):
        self._flush_cache()
        if token in self._cache and self._cache[token].get(k):
            return self._cache[token]

        rv = list(self.search({'token': token, k: v}))
        if len(rv) == 0:
            raise AuthError('unauthorized')

        self._cache[token] = rv[0]
        return rv[0]

    def admin(self, token):
        return self.check(token, 'admin')

    def read(self, token):
        return self.check(token, 'read')

    def write(self, token):
        return self.check(token, 'write')

    def last_activity_at(self, token):
        if token in self._cache and self._cache[token].get('last_activity_at'):
            return self._cache[token].get('last_activity_at')

        rv = list(self.search({'token': token}))

        if not rv:
            return None

        return rv[0].get('last_activity_at', None)

