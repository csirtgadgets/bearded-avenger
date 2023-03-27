from elasticsearch_dsl import Index
from elasticsearch import helpers
import elasticsearch.exceptions
from elasticsearch_dsl.connections import connections
from cif.store.indicator_plugin import IndicatorManagerPlugin
from cif.utils import strtobool
from cifsdk.exceptions import AuthError, CIFException
from datetime import datetime, timedelta
from cifsdk.constants import PYVERSION
import logging
from .helpers import expand_ip_idx, i_to_id
from .filters import filter_build
from .constants import LIMIT, WINDOW_LIMIT, TIMEOUT, UPSERT_MODE, PARTITION, \
    DELETE_FILTERS, UPSERT_MATCH, REQUEST_TIMEOUT, ReIndexError
from .locks import LockManager
from .schema import Indicator
import time
import os

logger = logging.getLogger('cif.store.zelasticsearch')
if PYVERSION > 2:
    basestring = (str, bytes)

UPSERT_TRACE = strtobool(os.environ.get('CIF_STORE_ES_UPSERT_TRACE', False))

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

        # idx exists now no matter what (either just created or was already present), 
        # but if new mappings added to Indicator schema since last startup, this will add those types to idx
        try:
            Indicator.init(index=self.idx)
        except elasticsearch.exceptions.RequestError:
            raise ReIndexError('Your Indicators index {} is using an old mapping'.format(self.idx))
        except Exception as e:
            raise ReIndexError('Unspecified error: {}'.format(e))

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
            logger.info('Creating new index')
            index = Index(idx)
            index.aliases(live={})
            index.doc_type(Indicator)
            index.settings(max_result_window=WINDOW_LIMIT)
            try:
                index.create()
            # after implementing auth to use cif_store, there appears to sometimes be a race condition
            # where both the normal store and the auth store don't see the index and then try to create simultaneously.
            # gracefully handle if that happens
            except elasticsearch.exceptions.TransportError as e:
                if (e.error.startswith('IndexAlreadyExistsException') or
                    e.error.startswith('index_already_exists_exception')):
                    pass
                else:
                    raise
            self.handle.indices.flush(idx)

        self.last_index_check = datetime.utcnow()
        self.last_index_value = idx
        return idx

    def search(self, token, filters, sort='reporttime', raw=False, sindex=False, timeout=TIMEOUT, find_relatives=False):
        limit = filters.get('limit', LIMIT)

        # search a given index - used in upserts
        if sindex:
            s = Indicator.search(index=sindex)
            find_relatives=False # don't find indicator relatives in upsert searches
        else:
            s = Indicator.search(index='{}-*'.format(self.indicators_prefix))
            # in non-upsert searches, permit finding relatives
            find_relatives = filters.get('find_relatives', False)

        s = s.params(size=limit, timeout=timeout, request_timeout=REQUEST_TIMEOUT)
        s = s.sort('-reporttime', '-lasttime')

        s = filter_build(s, filters, token=token, find_relatives=find_relatives)

        #logger.debug(s.to_dict())

        start = time.time()
        try:
            es = connections.get_connection(s._using)
            old_serializer = es.transport.deserializer

            if raw:
                rv = es.search(
                    index=s._index,
                    doc_type=s._doc_type,
                    body=s.to_dict(),
                    **s._params,
                    error_trace=UPSERT_TRACE
                    )

            else:
                es.transport.deserializer = self.Deserializer()

                rv = es.search(
                    index=s._index,
                    doc_type=s._doc_type,
                    body=s.to_dict(),
                    filter_path=['hits.hits._source'],
                    **s._params,
                    error_trace=UPSERT_TRACE)
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
            return

        logger.debug('query took: %0.2f' % (time.time() - start))

        return rv

    def create(self, token, data, raw=False, bulk=False):
        index = self._create_index()

        expand_ip_idx(data)
        id = i_to_id(data)

        if data.get('group') and type(data['group']) != list:
            data['group'] = [data['group']]

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

        # Create current index if needed
        index = self._create_index()

        count = 0

        # http://stackoverflow.com/questions/30111258/elasticsearch-in-equivalent-operator-in-elasticsearch

        # aggregate indicators based on dedup criteria
        agg = {}
        for d in sorted(indicators, key=lambda k: k['lasttime'], reverse=True):
            key = []

            for v in UPSERT_MATCH:

                if d.get(v):
                    if isinstance(d[v], basestring):
                        key.append(d[v])
                    elif isinstance(d[v], float) or isinstance(d[v], int):
                        key.append(str(d[v]))
                    elif isinstance(d[v], list):
                        for k in d[v]:
                            key.append(k)

            key = "_".join(key)

            # already seen in batch
            if key in agg:
                # look for older first times
                if d.get('firsttime') < agg[key].get('firsttime'):
                    agg[key]['firsttime'] = d['firsttime']
                    if d.get('count'):
                        agg[key]['count'] = agg[key].get('count') + d.get('count')

            # haven't yet seen in batch
            else:
                agg[key] = d

        actions = []

        #self.lockm.lock_aquire()
        for d in agg:
            d = agg[d]

            # start assembling search filters
            filters = {'limit': 1}
            for x in UPSERT_MATCH:
                if d.get(x):
                    if x == 'confidence':
                        filters[x] = '{},{}'.format(d[x], d[x])
                    elif x == 'group':
                        # indicator submit api expects 'group' (singular)
                        # but search api expects 'groups' (plural)
                        filters['groups'] = d[x]
                    elif x == 'rdata':
                        # if wildcard in rdata, don't add it to upsert search; 
                        # urls can contain asterisks, and complex wildcard queries can 
                        # create ES timeouts
                        if '*' not in d['rdata']:
                            filters[x] = d[x]
                    else:
                        filters[x] = d[x]

            # search for existing, return latest record
            try:
                # search the current index only
                filters['sort'] = '-reporttime,-lasttime'
                rv = self.search(token, filters, raw=True, sindex=index)
            except Exception as e:
                logger.error(e)
                raise e
            
            try:
                rv = rv['hits']['hits']
            except Exception as e:
                raise CIFException(e)

            # Indicator does not exist in results
            if len(rv) == 0:
                if not d.get('count'):
                    d['count'] = 1

                if d.get('group') and type(d['group']) != list:
                    d['group'] = [d['group']]

                expand_ip_idx(d)

                # append create to create set
                if UPSERT_TRACE:
                    logger.debug('upsert: creating new {}'.format(d['indicator']))
                actions.append({
                    '_index': index,
                    '_type': 'indicator',
                    '_source': d,
                })

                count += 1
                continue

            # Indicator exists in results
            else:
                if UPSERT_TRACE:
                    logger.debug('upsert: match indicator {}'.format(rv[0]['_id']))

                # map result
                i = rv[0]

                # skip new indicators that don't have a more recent lasttime
                if not self._is_newer(d, i['_source']):
                    logger.debug('skipping...')
                    continue

                # map existing indicator
                i = i['_source']

                # we're working within the same index
                if rv[0]['_index'] == self._current_index():

                    # update fields
                    i['count'] += 1
                    i['lasttime'] = d['lasttime']
                    i['reporttime'] = d['reporttime']

                    # if existing indicator doesn't have message field but new indicator does, add new message to upsert
                    if d.get('message'):
                        if not i.get('message'):
                            i['message'] = []

                        i['message'].append(d['message'])

                    # always update description if it exists
                    if d.get('description'):
                        i['description'] = d['description']

                    # append update to create set
                    if UPSERT_TRACE:
                        logger.debug('upsert: updating same index {}, {}'.format(d.get('indicator'), rv[0]['_id']))
                    actions.append({
                        '_op_type': 'update',
                        '_index': rv[0]['_index'],
                        '_type': 'indicator',
                        '_id': rv[0]['_id'],
                        '_body': {'doc': i}
                    })

                    count += 1
                    continue

                # if we aren't in the same index
                else:

                    # update fields
                    i['count'] = i['count'] + 1
                    i['lasttime'] = d['lasttime']
                    i['reporttime'] = d['reporttime']

                    # if existing indicator doesn't have message field but new indicator does, add new message to upsert
                    if d.get('message'):
                        if not i.get('message'):
                            i['message'] = []

                        i['message'].append(d['message'])

                    # always update description if exists
                    if d.get('description'):
                        i['description'] = d['description']

                    # append create to create set
                    if UPSERT_TRACE:
                        logger.debug('upsert: updating across index {}'.format(d['indicator']))
                    actions.append({
                        '_index': index,
                        '_type': 'indicator',
                        '_source': i,
                    })

                    # delete the old document
                    if UPSERT_TRACE:
                        logger.debug('upsert: deleting old index {}, {}'.format(d['indicator'], rv[0]['_id']))

                    actions.append({
                        '_op_type': 'delete',
                        '_index': rv[0]['_index'],
                        '_type': 'indicator',
                        '_id': rv[0]['_id']
                    })

                    count += 1
                    continue


        if len(actions) > 0:
            try:
                helpers.bulk(self.handle, actions)
            except helpers.BulkIndexError as e:
                if e.errors[0]['index']['status'] == 409:
                    # version conflict error, prob just modified by another mp process
                    logger.error(e)
                else:
                    raise e
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
            q_filters['sort'] = '-reporttime,-lasttime'
            rv = self.search(token, q_filters, raw=True)
            rv = rv.get('hits').get('hits')
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
