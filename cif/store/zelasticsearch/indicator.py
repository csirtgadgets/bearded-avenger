import logging
import arrow
import time
from datetime import datetime, timedelta

from elasticsearch import helpers
import elasticsearch.exceptions
from elasticsearch_dsl import Index
from elasticsearch_dsl.connections import connections

from cifsdk.exceptions import AuthError
from cifsdk.constants import PYVERSION
from cif.store.indicator_plugin import IndicatorManagerPlugin

from .helpers import expand_ip_idx, i_to_id
from .filters import filter_build
from .constants import LIMIT, WINDOW_LIMIT, TIMEOUT, PARTITION
from .schema import Indicator

logger = logging.getLogger('cif.store.zelasticsearch')
if PYVERSION > 2:
    basestring = (str, bytes)


class IndicatorManager(IndicatorManagerPlugin):
    class Deserializer(object):
        def __init__(self):
            pass

        def loads(self, s, mimetype=None):
            return s

    def __init__(self, *args, **kwargs):
        super(IndicatorManager, self).__init__(*args, **kwargs)

        self.indicators_prefix = kwargs.get('indicators_prefix', 'indicators')
        self.partition = PARTITION
        self.idx = self._current_index()
        self.last_index_check = datetime.now() - timedelta(minutes=5)
        self.handle = connections.get_connection()

        self._create_index()

    def flush(self):
        self.handle.indices.flush(index=self._current_index())

    def _current_index(self):
        dt = datetime.utcnow()
        dt = dt.strftime('%Y.%m')

        if self.partition == 'day':
            dt = dt.strftime('%Y.%m.%d')

        if self.partition == 'year':
            dt = dt.strftime('%Y')

        idx = '{}-{}'.format(self.indicators_prefix, dt)
        return idx

    def _create_index(self):
        idx = self._current_index()

        # every time we check it does a HEAD req
        if (datetime.utcnow() - self.last_index_check) < timedelta(minutes=2):
            return idx

        if not self.handle.indices.exists(idx):
            index = Index(idx)
            index.aliases(live={})
            index.doc_type(Indicator)
            index.settings(max_result_window=WINDOW_LIMIT)
            index.create()
            self.handle.indices.flush(idx)

        self.last_index_check = datetime.utcnow()
        return idx

    def search(self, token, filters, sort='reporttime', raw=False, timeout=TIMEOUT):
        limit = filters.get('limit', LIMIT)

        s = Indicator.search(index='{}-*'.format(self.indicators_prefix))
        s = s.params(size=limit, timeout=timeout)
        s = s.sort('-reporttime', '-lasttime')

        s = filter_build(s, filters, token=token)

        logger.debug(s.to_dict())

        start = time.time()
        try:
            es = connections.get_connection(s._using)
            old_serializer = es.transport.deserializer
            es.transport.deserializer = self.Deserializer()
            rv = es.search(
                index=s._index,
                doc_type=s._doc_type,
                body=s.to_dict(),
                filter_path=['hits.hits._source'],
                **s._params)
            # transport caches this, so the tokens mis-fire
            es.transport.deserializer = old_serializer
        except elasticsearch.exceptions.RequestError as e:
            logger.error(e)
            es.transport.deserializer = old_serializer
            return

        logger.debug('query took: %0.2f' % (time.time() - start))

        return rv

    def create(self, token, data, raw=False, bulk=False):
        index = self._create_index()

        expand_ip_idx(data)
        id = i_to_id(data)

        if data.get('group') and type(data['group']) != list:
            data['group'] = [data['group']]

        if not data.get('lasttime'):
            data['lasttime'] = arrow.utcnow().datetime.replace(tzinfo=None)

        if not data.get('firsttime'):
            data['firsttime'] = data['lasttime']

        if not data.get('reporttime'):
            data['reporttime'] = data['lasttime']

        if bulk:
            d = {
                '_index': index,
                '_type': 'indicator',
                '_source': data
            }
            return d

        data['meta'] = {}
        data['meta']['index'] = index
        data['meta']['id'] = id
        i = Indicator(**data)

        if not i.save():
            raise AuthError('indicator exists')

        if raw:
            return i

        return i.to_dict()

    def create_bulk(self, token, indicators, flush=False):
        actions = []
        for i in indicators:
            ii = self.create(token, i, bulk=True)
            actions.append(ii)

        helpers.bulk(self.handle, actions, index=self._current_index())

        if flush:
            self.flush()

        return len(actions)

    def upsert(self, token, indicators, flush=False):
        return self.create_bulk(token, indicators, flush=flush)