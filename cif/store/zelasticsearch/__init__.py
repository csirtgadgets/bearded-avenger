import logging
import os

from cifsdk.exceptions import CIFException
from cif.store.plugin import Store
from cif.store.zelasticsearch.token import TokenManager
from cif.store.zelasticsearch.indicator import IndicatorManager
from cif.utils import strtobool
from elasticsearch_dsl.connections import connections
from elasticsearch.exceptions import ConnectionError
import traceback
from time import sleep

ES_NODES = os.getenv('CIF_ES_NODES', '127.0.0.1:9200')
TRACE = strtobool(os.environ.get('CIF_STORE_ES_TRACE', False))
TRACE_HTTP = strtobool(os.environ.get('CIF_STORE_ES_HTTP_TRACE', False))

logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)

logging.getLogger('urllib3').setLevel(logging.ERROR)
logging.getLogger('elasticsearch').setLevel(logging.ERROR)

if TRACE:
    logger.setLevel(logging.DEBUG)

if TRACE_HTTP:
    logging.getLogger('urllib3').setLevel(logging.INFO)
    logging.getLogger('elasticsearch').setLevel(logging.DEBUG)


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
        self.token_cache = kwargs.get('token_cache', {})

        logger.info('setting es nodes {}'.format(nodes))

        connections.create_connection(hosts=nodes)

        self._alive = False

        while not self._alive:
            if not self._health_check():
                logger.warn('ES cluster not accessible')
                logger.info('retrying connection in 30s')
                sleep(30)

            self._alive = True

        logger.info('ES connection successful')
        logger.info('CIF_STORE_ES_HTTP_TRACE set to {}'.format(TRACE_HTTP))
        self.tokens = TokenManager(token_cache=self.token_cache)
        self.indicators = IndicatorManager()

    def _health_check(self):
        try:
            x = connections.get_connection().cluster.health()
        except ConnectionError as e:
            logger.warn('elasticsearch connection error')
            logger.error(e)
            return

        except Exception as e:
            logger.error(traceback.print_exc())
            return

        logger.info('ES cluster is: %s' % x['status'])
        return x

    def ping(self):
        s = self._health_check()

        if s is None or s['status'] == 'red':
            raise CIFException('ES Cluster Issue')

        return True


Plugin = _ElasticSearch
