from cif.store import Store
from pprint import pprint


class Dummy(Store):

    name = 'dummy'

    def __init__(self, *args, **kwargs):
        #super(Plugin, self).__init__(*args, **kwargs)
        pass

    def tokens_admin_exists(self):
        return True

    def tokens_create(self, data):
        return [data]

    def tokens_delete(self, data):
        return [data]

    def tokens_search(self, token, data):
        return [data]

    def token_admin(self, token):
        return True

    def token_read(self, token):
        return True

    def token_write(self, token):
        return True

    def search(self, token, data):
        return [data]

    def submit(self, token, data):
        return [data]

    def token_last_activity_at(self, token, timestamp=None):
        return timestamp

Plugin = Dummy