from datetime import datetime
import elasticsearch
from elasticsearch_dsl.connections import connections
from time import sleep
from cif.exceptions import StoreLockError
import os
import socket

LOCK_RETRIES = 45
LOCK_RETRIES = os.getenv('CIF_ES_LOCK_RETRIES', LOCK_RETRIES)
TEST_MODE = os.getenv('CIF_ELASTICCSEARCH_TEST', 0)
LOCKS_FORCE = os.getenv('CIF_ES_LOCK_FORCE', 0)


class LockManager(object):
    def __init__(self, handle, logger):
        self.lock = False
        self.handle = handle
        self.logger = logger
        self.name = socket.gethostname()
        self.nodes = self._nodes()

    def _nodes(self):
        info = elasticsearch.client.NodesClient(self.handle).info()
        return int(info['_nodes']['total'])

    def lock_aquire(self):
        if TEST_MODE:
            return

        if self.nodes == 1 and not LOCKS_FORCE:
            return

        es = self.handle
        n = int(LOCK_RETRIES)
        while not self.lock and n > 0:
            try:
                es.create(
                    index='fs', doc_type='lock', id='global',
                    body={'timestamp': datetime.utcnow(), 'node': self.name})
                self.lock = True
            except elasticsearch.exceptions.TransportError as e:
                l = es.get(index='fs', doc_type='lock', id='global')
                self.logger.debug(l)
                self.logger.info('waiting on global lock from %s %s' % (l['_source']['node'], l['_source']['timestamp']))
                n -= 1
                sleep(2)

        if n == 0:
            raise StoreLockError('failed to acquire lock')

    def lock_release(self):
        if TEST_MODE:
            return

        if self.nodes == 1 and not LOCKS_FORCE:
            return

        self.handle.delete(index='fs', doc_type='lock', id='global')
        self.lock = False
