from cif.stores.base import Store
from pprint import pprint


class Plugin(Store):

    name = 'dummy'

    def __init__(self, *args, **kwargs):
        super(Plugin, self).__init__(*args, **kwargs)

    def auth_read(self, token):
        return True

    def auth_write(self):
        return True

    def search(self, data):
        return [{
            "observable": data['observable']
        }]

    def submit(self, data):
        pprint(data)
        return [{
            "subject": data['subject']
        }]