from cif.store.plugin import Store
from pprint import pprint


class Dummy(Store):

    name = 'dummy'

    def __init__(self, *args, **kwargs):
        pass

    def tokens_admin_exists(self):
        return False

    def tokens_create(self, data):
        data['token'] = self._token_generate()
        return data

    def tokens_delete(self, data):
        return [data]

    def tokens_search(self, data):
        return [data]

    def token_admin(self, token):
        return True

    def token_read(self, token):
        return True

    def token_write(self, token):
        return True

    def indicators_search(self, token, data):
        return [data]

    def indicators_create(self, token, data):
        return [data]

    def indicators_upsert(self, token, data):
        return [data]

    def token_last_activity_at(self, token, timestamp=None):
        return timestamp

    def token_edit(self, data):
        return data

    def ping(self):
        return True

Plugin = Dummy