try:
    from elasticsearch import Elasticsearch
except ImportError:
    raise SystemExit('Requires Elasticsearch to be installed')

from cif.store import Store


## TODO -- sep plugin
class Plugin(Store):

    name = 'elasticsearch'

    def __init__(self, *args, **kwargs):
        super(Plugin, self).__init__(*args, **kwargs)