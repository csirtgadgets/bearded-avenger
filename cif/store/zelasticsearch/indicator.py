from elasticsearch_dsl import Index
from elasticsearch import helpers
import elasticsearch.exceptions
from elasticsearch_dsl.connections import connections
from cif.store.indicator_plugin import IndicatorManagerPlugin
from pprint import pprint
from cifsdk.exceptions import AuthError, CIFException
from datetime import datetime, timedelta
from cifsdk.constants import PYVERSION
import logging
import json
from .helpers import expand_ip_idx, i_to_id
from .filters import filter_build
from .constants import LIMIT, WINDOW_LIMIT, TIMEOUT, UPSERT_MODE, PARTITION, DELETE_FILTERS
from .locks import LockManager
from .schema import Indicator
import arrow
import time

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
        self.last_index_value = None
        self.handle = connections.get_connection()
        self.lockm = LockManager(self.handle, logger)

        self._create_index()

    def flush(self):
        self.handle.indices.flush(index=self._current_index())

    def _current_index(self):
        dt = datetime.utcnow()

        if self.partition == 'month':  # default partition setting
            dt = dt.strftime('%Y.%m')

        if self.partition == 'day':
            dt = dt.strftime('%Y.%m.%d')

        if self.partition == 'year':
            dt = dt.strftime('%Y')

        idx = '{}-{}'.format(self.indicators_prefix, dt)
        return idx

    def _create_index(self):
        # https://github.com/csirtgadgets/massive-octo-spice/blob/develop/elasticsearch/observables.json
        # http://elasticsearch-py.readthedocs.org/en/master/api.html#elasticsearch.Elasticsearch.bulk

        # every time we check it does a HEAD req
        if self.last_index_value and (datetime.utcnow() - self.last_index_check) < timedelta(minutes=2):
            return self.last_index_value

        idx = self._current_index()

        if not self.handle.indices.exists(idx):
            index = Index(idx)
            index.aliases(live={})
            index.doc_type(Indicator)
            index.settings(max_result_window=WINDOW_LIMIT)
            index.create()
            self.handle.indices.flush(idx)

        self.last_index_check = datetime.utcnow()
        self.last_index_value = idx
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

            if raw:
                rv = es.search(
                    index=s._index,
                    doc_type=s._doc_type,
                    body=s.to_dict(),
                    **s._params)
            else:
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
        # catch all other es errors
        except elasticsearch.ElasticsearchException as e:
            logger.error(e)
            es.transport.deserializer = old_serializer
            raise CIFException

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

        try:
            helpers.bulk(self.handle, actions, index=self._current_index())

        except Exception as e:
            logger.error(e)
            actions = []

        if flush:
            self.flush()

        return len(actions)

    def upsert(self, token, indicators, flush=False):
        if not UPSERT_MODE:
            return self.create_bulk(token, indicators, flush=flush)

        count = 0
        was_added = {}  # to deal with es flushing

        # http://stackoverflow.com/questions/30111258/elasticsearch-in-equivalent-operator-in-elasticsearch

        sorted(indicators, key=lambda k: k['reporttime'], reverse=True)
        actions = []

        #self.lockm.lock_aquire()
        for d in indicators:
            if was_added.get(d['indicator']):
                for first in was_added[d['indicator']]: break
                if d.get('reporttime') and d['reporttime'] < first:
                    continue

            filters = {
                'indicator': d['indicator'],
                'provider': d['provider'],
                'limit': 1
            }

            if d.get('tags'):
                filters['tags'] = d['tags']

            if d.get('rdata'):
                filters['rdata'] = d['rdata']

            rv = list(self.search(token, filters, sort='reporttime', raw=True))

            if len(rv) == 0:
                if was_added.get(d['indicator']):
                    if d.get('lasttime') in was_added[d['indicator']]:
                        logger.debug('skipping: %s' % d['indicator'])
                        continue
                else:
                    was_added[d['indicator']] = set()

                if not d.get('count'):
                    d['count'] = 1

                if d.get('group') and type(d['group']) != list:
                    d['group'] = [d['group']]

                self._timestamps_fix(d)
                expand_ip_idx(d)

                actions.append({
                    '_index': self._current_index(),
                    '_type': 'indicator',
                    '_source': d,
                })

                was_added[d['indicator']].add(d['reporttime'])
                count += 1
                continue

            i = rv[0]
            if not self._is_newer(d, i['_source']):
                logger.debug('skipping...')
                continue

            # carry the index'd data forward and remove the old index
            # TODO- don't we already have this via the search?
            #i = self.handle.get(index=r['_index'], doc_type='indicator', id=r['_id'])
            i = i['_source']

            # we're working within the same index
            if rv[0]['_index'] == self._current_index():
                i['count'] += 1
                i['lasttime'] = d['lasttime']
                i['reporttime'] = d['lasttime']

                if d.get('message'):
                    if not i.get('message'):
                        i['message'] = []

                    i['message'].append(d['message'])

                actions.append({
                    '_op_type': 'update',
                    '_index': rv[0]['_index'],
                    '_type': 'indicator',
                    '_id': rv[0]['_id'],
                    '_body': {'doc': i}
                })
                continue

            # carry the information forward into the next month's index
            d['count'] = i['count'] + 1
            i['lasttime'] = d['lasttime']
            i['reporttime'] = d['lasttime']

            if d.get('message'):
                if not i.get('message'):
                    i['message'] = []

                i['message'].append(d['message'])

            # delete the old document
            actions.append({
                '_op_type': 'delete',
                '_index': rv[0]['_index'],
                '_type': 'indicator',
                '_id': rv[0]['_id']
            })

        if len(actions) > 0:
            try:
                helpers.bulk(self.handle, actions)
            except Exception as e:
                #self.lockm.lock_release()
                raise e

        if flush:
            self.flush()

        #self.lockm.lock_release()
        return count


    def delete(self, token, data, id=None, flush=True):

        q_filters = {}
        for x in DELETE_FILTERS:
            if data.get(x):
                q_filters[x] = data[x]

        logger.debug(q_filters)

        if len(q_filters) == 0:
            return '0, must specify valid filter. valid filters: {}'.format(DELETE_FILTERS)

        try:
           rv = self.search(token, q_filters, sort='reporttime', raw=True)
           rv = rv['hits']['hits']
        except Exception as e:
            raise CIFException(e)

        logger.debug('delete match: {}'.format(rv))

        # docs matched
        if len(rv) > 0:
            actions = []
            for i in rv:
                actions.append({
                    '_op_type': 'delete',
                    '_index': i['_index'],
                    '_type': 'indicator',
                    '_id': i['_id']
                })

            try:
                helpers.bulk(self.handle, actions)
            except Exception as e:
                raise CIFException(e)

            if flush:
                self.flush()

            logger.info('{} deleted {} indicators'.format(token['username'], len(rv)))
            return len(rv)


        # no matches, return 0
        return 0
