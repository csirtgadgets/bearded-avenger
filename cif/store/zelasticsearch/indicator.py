from elasticsearch_dsl import DocType, String, Date, Integer, Float, Ip, Mapping, Index, GeoPoint, Byte, MetaField
from elasticsearch import helpers
import elasticsearch.exceptions
from elasticsearch_dsl.connections import connections
from cif.store.indicator_plugin import IndicatorManagerPlugin
from pprint import pprint
from cifsdk.exceptions import AuthError
from datetime import datetime, timedelta
from cifsdk.constants import PYVERSION
import logging
import json
from .helpers import expand_ip_idx, i_to_id
from .filters import filter_build
from .constants import LIMIT, WINDOW_LIMIT, TIMEOUT, LOGSTASH_MODE
from .locks import LockManager
from .schema import Indicator

logger = logging.getLogger('cif.store.zelasticsearch')
if PYVERSION > 2:
    basestring = (str, bytes)


class IndicatorManager(IndicatorManagerPlugin):

    def __init__(self, *args, **kwargs):
        super(IndicatorManager, self).__init__(*args, **kwargs)

        self.indicators_prefix = kwargs.get('indicators_prefix', 'indicators')
        self.idx = self._current_index()
        self.last_index_check = datetime.now() - timedelta(minutes=5)
        self.handle = connections.get_connection()
        self.lockm = LockManager(self.handle, logger)

        self._create_index()

    def flush(self):
        self.handle.indices.flush(index=self._current_index())

    def _current_index(self):
        dt = datetime.utcnow()
        dt = dt.strftime('%Y.%m')
        idx = '{}-{}'.format(self.indicators_prefix, dt)
        return idx

    def _create_index(self):
        # https://github.com/csirtgadgets/massive-octo-spice/blob/develop/elasticsearch/observables.json
        # http://elasticsearch-py.readthedocs.org/en/master/api.html#elasticsearch.Elasticsearch.bulk
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

            m = Mapping('indicator')
            m.field('indicator_ipv4', 'ip')
            m.field('indicator_ipv4_mask', 'integer')
            m.field('lasttime', 'date')
            m.save(idx)

        self.last_index_check = datetime.utcnow()
        return idx

    def search(self, token, filters, sort='reporttime', raw=False, timeout=TIMEOUT):
        limit = filters.get('limit', LIMIT)

        s = Indicator.search(index='{}-*'.format(self.indicators_prefix))
        s = s.params(size=limit, timeout=timeout, sort=sort)

        s = filter_build(s, filters, token=token)

        logger.debug(json.dumps(s.to_dict(), indent=4))

        try:
            rv = s.execute()
        except elasticsearch.exceptions.RequestError as e:
            logger.error(e)
            return

        if not rv.hits.hits:
            return

        for r in rv.hits.hits:
            if raw:
                yield r
            else:
                yield r['_source']

    def create(self, token, data, raw=False, bulk=False):
        index = self._create_index()

        expand_ip_idx(data)
        id = i_to_id(data)
        ts = data.get('reporttime', data['lasttime'])

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

    def create_bulk(self, token, indicators):
        actions = []
        for i in indicators:
            ii = self.create(token, i, bulk=True)
            actions.append(ii)

        helpers.bulk(self.handle, actions)

        return [i['_source'] for i in actions]

    def upsert(self, token, indicators, flush=False):
        if LOGSTASH_MODE:
            return self.create_bulk(token, indicators)

        count = 0
        was_added = {}  # to deal with es flushing

        # http://stackoverflow.com/questions/30111258/elasticsearch-in-equivalent-operator-in-elasticsearch

        sorted(indicators, key=lambda k: k['reporttime'], reverse=True)
        actions = []

        self.lockm.lock_aquire()
        for d in indicators:
            if was_added.get(d['indicator']):
                for first in was_added[d['indicator']]: break
                if d['lasttime'] < first:
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
                self.lockm.lock_release()
                raise e

        if flush:
            self.flush()
        self.lockm.lock_release()
        return count

