try:
    from elasticsearch import Elasticsearch
except ImportError:
    raise SystemExit('Requires Elasticsearch to be installed')

from cif.store import Store
import logging


class ElasticSearch_(Store):

    name = 'elasticsearch'

    def __init__(self, nodes=[]):
        self.logger = logging.getLogger(__name__)

    def indicator_create(self, token, data):
        return data

    def indicator_search(self, token, data):
        return data

    def ping(self, token):
        return True

    def tokens_admin_exists(self):
        return True

    def tokens_create(self, data):
        return True

    def tokens_delete(self, data):
        return True

    def tokens_search(self, data):
        return True

    def token_admin(self, token):
        return True

    def token_read(self, token):
        return True

    def token_write(self, token):
        return True

    def token_edit(self, data):
        return True

    def token_last_activity_at(self, token, timestamp=None):
        return True

Plugin = ElasticSearch_
