from cif.store import Store


class Graph(Store):

    name = 'graph'

    def __init__(self, *args, **kwargs):
        super(Plugin, self).__init__(*args, **kwargs)

    def auth_read(self, token):
        return True

    def auth_write(self):
        return True

    def search(self, data):
        return [data]

    def submit(self, data):
        return [data]

Plugin = Graph