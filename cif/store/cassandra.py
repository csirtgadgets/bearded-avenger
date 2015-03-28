from cif.stores.base import Store


class Plugin(Store):

    name = 'cassandra'

    def __init__(self, *args, **kwargs):
        super(Plugin, self).__init__(*args, **kwargs)