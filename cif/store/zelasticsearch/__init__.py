import logging
import os

from cif.store.plugin import Store
from cif.store.zelasticsearch.token import TokenManager
from cif.store.zelasticsearch.indicator import IndicatorManager
from elasticsearch_dsl.connections import connections
from elasticsearch.exceptions import ConnectionError
import traceback
from time import sleep
from cif.constants import TOKEN_CACHE_DELAY
import arrow
from cif.constants import PYVERSION

ES_NODES = os.getenv('CIF_ES_NODES', '127.0.0.1:9200')
TRACE = os.environ.get('CIF_STORE_ES_TRACE')
TRACE_HTTP = os.getenv('CIF_STORE_ES_HTTP_TRACE')

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

if not TRACE:
    logger.setLevel(logging.ERROR)

    es_logger = logging.getLogger('elasticsearch')
    es_logger.propagate = False
    es_logger.setLevel(logging.ERROR)

if not TRACE_HTTP:
    urllib_logger = logging.getLogger('urllib3')
    urllib_logger.setLevel(logging.ERROR)
    es_logger = logging.getLogger('elasticsearch')
    es_logger.setLevel(logging.ERROR)


class _ElasticSearch(Store):
    # http://stackoverflow.com/questions/533631/what-is-a-mixin-and-why-are-they-useful

    name = 'elasticsearch'

    def __init__(self, nodes=ES_NODES, **kwargs):

        if type(nodes) == str:
            nodes = nodes.split(',')

        if not nodes:
            nodes = ES_NODES

        self.indicators_prefix = kwargs.get('indicators_prefix', 'indicators')
        self.tokens_prefix = kwargs.get('tokens_prefix', 'tokens')

        logger.info('setting es nodes {}'.format(nodes))

        connections.create_connection(hosts=nodes)

        self._alive = False

        while not self._alive:
            if not self.ping():
                logger.warn('ES cluster not accessible')
                logger.info('retrying connection in 30s')
                sleep(30)

            self._alive = True

        logger.info('ES connection successful')
        self.tokens = TokenManager()
        self.indicators = IndicatorManager()

    def ping(self):
        # http://elasticsearch-py.readthedocs.org/en/master/api.html#elasticsearch.client.IndicesClient.stats

        try:
            x = connections.get_connection().cluster.health()
        except ConnectionError as e:
            logger.warn('elasticsearch connection error')
            logger.error(e)
            return

        except Exception as e:
            logger.error(traceback.print_exc())
            return

        if x['status'] in ['green', 'yellow']:
            logger.info('ES cluster is: %s' % x['status'])
            return True

        logger.warn('ES Cluster RED')

Plugin = _ElasticSearch
