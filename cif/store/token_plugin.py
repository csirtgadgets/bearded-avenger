import arrow
from cif.constants import TOKEN_CACHE_DELAY
from cifsdk.exceptions import AuthError


class TokenPlugin(object):

    def _token_flush_cache(self):
        if arrow.utcnow().timestamp > self.token_cache_check:
            self.token_cache = {}
            self.token_cache_check = arrow.utcnow().timestamp + TOKEN_CACHE_DELAY

    def _token_cache_check(self, token, k=None):
        self._token_flush_cache()
        if token not in self.token_cache:
            return False

        return self.token_cache[token]

    def tokens_admin_exists(self):
        t = list(self.tokens_search({'admin': True}))
        if len(t) > 0:
            return t[0]['token']

    def token_check(self, token, k, v=True):
        if token in self.token_cache and self.token_cache[token].get(k):
            return self.token_cache[token]

        return list(self.tokens_search({'token': token, k: v}))

    def token_admin(self, token):
        self._token_flush_cache()
        x = self.token_check(token, 'admin')
        if len(x) > 0:
            return True

        raise AuthError('unauthorized')

    def token_read(self, token):
        x = self.token_check(token, 'read')
        if len(x) > 0:
            return True

        raise AuthError('unauthorized')

    def token_write(self, token):
        x = self.token_check(token, 'write')
        if len(x) > 0:
            return True

        raise AuthError('unauthorized')

    def token_last_activity_at(self, token):

        if token in self.token_cache and self.token_cache[token].get('last_activity_at'):
            return self.token_cache[token].get('last_activity_a')

        rv = list(self.tokens_search({'token': token}))

        if not rv:
            return None

        return rv[0].get('last_activity_at', None)

