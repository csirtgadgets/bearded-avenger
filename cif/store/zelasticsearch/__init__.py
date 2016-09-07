import logging
import os

from cif.store.plugin import Store
from cif.store.zelasticsearch.token import TokenMixin
from cif.store.zelasticsearch.indicator import IndicatorMixin
from elasticsearch_dsl.connections import connections

ES_NODES = os.getenv('CIF_ES_NODES', '127.0.0.1:9200')


class _ElasticSearch(IndicatorMixin, TokenMixin, Store):
    # http://stackoverflow.com/questions/533631/what-is-a-mixin-and-why-are-they-useful

    name = 'elasticsearch'

    def __init__(self, nodes=ES_NODES):
        self.logger = logging.getLogger(__name__)

        if type(nodes) == str:
            nodes = nodes.split(',')

        self.logger.info('setting es nodes {}'.format(nodes))
        connections.create_connection(hosts=nodes)

    def ping(self, token):
        # http://elasticsearch-py.readthedocs.org/en/master/api.html#elasticsearch.client.IndicesClient.stats
        x = connections.get_connection().cluster.health()

        if ('green', 'yellow') in x['status']:
            return True

Plugin = _ElasticSearch

