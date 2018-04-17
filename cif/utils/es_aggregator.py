try:
    import elasticsearch
except ImportError:
    print('this module requires the elasticsearch library')
    raise ImportError

from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter
import logging
import textwrap
from elasticsearch import Elasticsearch
from elasticsearch_dsl.connections import connections
from datetime import datetime
from dateutil.relativedelta import relativedelta
from elasticsearch import helpers
from cif.store.zelasticsearch.indicator import Index, Indicator
from cif.store.zelasticsearch.constants import WINDOW_LIMIT
import re
from cif.constants import VERSION
from cifsdk.utils import setup_logging
from pprint import pprint
import os
import uuid
from hashlib import sha256

CONFIDENCE = 50
MONTHS = 12
LIMIT = 5000


def _id_deterministic(i):
    tags = ','.join(sorted(i['tags']))
    groups = ','.join(sorted(i['group']))

    id = ','.join([groups, i['provider'], i['indicator'], tags])
    ts = i.get('lasttime')
    if ts:
        id = '{},{}'.format(id, ts)

    return id


def i_to_id(i):
    #id = _id_random(i)
    id = _id_deterministic(i)
    return sha256(id.encode('utf-8')).hexdigest()


def main():

    p = ArgumentParser(
        description=textwrap.dedent('''\
        example usage:
            $ cif-es-archive
        '''),
        formatter_class=RawDescriptionHelpFormatter,
        prog='cif-es-archive'
    )

    # options
    p.add_argument("-v", "--verbose", action="store_true", help="logging level: INFO")
    p.add_argument('-d', '--debug', action="store_true", help="logging level: DEBUG")
    p.add_argument('-V', '--version', action='version', version=VERSION)
    p.add_argument('--dry-run', action="store_true", help='dry run, do not delete')
    p.add_argument('--nodes', default=['localhost:9200'])
    p.add_argument('--year', default='2017')

    if not os.getenv('CIF_ELASTICSEARCH_TEST', False) == '1':
        raise SystemError('This has NOT been tested yet, remove this line to test at your own risk!')

    args = p.parse_args()
    setup_logging(args)
    logger = logging.getLogger(__name__)

    connections.create_connection(hosts=args.nodes, timeout=(60 * 30))
    es = connections.get_connection()

    # setup the query
    q = {
        'sort': [
            {'reporttime': {'order': 'asc'}},
            {'indicator': {'order': 'asc'}}
        ],
    }
    cache = {}
    actions = []

    # scroll through docs
    for data in elasticsearch.helpers.scan(es, q, preserve_order=True, index='indicators-2017'):
        # check to see if we've seen this before
        i = data['_source']
        cache_id = data['_id']
        id = _id_deterministic(i)

        if id not in cache:
            # if not, store key, and continue
            cache[id] = data
            continue

        pprint(cache[i['indicator']])

        # if yes, update last/reporttime/count for doc id
        actions.append({
            '_op_type': 'update',
            '_index': 'indicators-2017',
            '_type': 'indicator',
            '_id': cache[i['indicator']]['_id'],
            "retry_on_conflict": 3,
            'doc': {
                'lasttime': i['lasttime'],
                'reporttime': i['reporttime'],
            },
            "_source": {
                "script": {
                    "source": "ctx._source.count += params.param1",
                    "lang": "painless",
                    "params": {"param1": 1}
                },
                "upsert": {"count": 1}
            }
        })

        # delete doc and continue
        actions.append({
            '_op_type': 'delete',
            '_index': 'indicators-2017',
            '_type': 'indicator',
            '_id': cache_id,
        })

    rv = elasticsearch.helpers.bulk(es, actions)
    pprint(rv)
    assert rv[0] > 0

    # cleanup
    es.indices.forcemerge(index='indicators-2017')


if __name__ == "__main__":
    main()
