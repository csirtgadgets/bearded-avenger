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

CONFIDENCE = 50
MONTHS = 12
LIMIT = 5000


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
    p.add_argument('-m', '--months', help='how many months ago to archive [default %(default)s]', default=MONTHS)
    p.add_argument('--dry-run', action="store_true", help='dry run, do not delete')
    p.add_argument('--nodes', default=['localhost:9200'])
    p.add_argument('--limit', help='specify scroll batch limit [default %(default)s]', default=LIMIT)

    if not os.getenv('CIF_ELASTICSEARCH_TEST', False) == '1':
        raise SystemError('This has NOT been tested yet, remove this line to test at your own risk!')

    args = p.parse_args()
    setup_logging(args)
    logger = logging.getLogger(__name__)

    end_month = (datetime.today() - relativedelta(months=int(args.months)))
    end_month = end_month.strftime('%Y.%m')

    logger.info('month: {}'.format(end_month))

    # es = Elasticsearch(hosts=args.nodes, timeout=120, max_retries=10, retry_on_timeout=True)
    connections.create_connection(hosts=args.nodes, timeout=(60 * 30))
    es = connections.get_connection()

    monthlies = es.indices.get_alias(index='{}-*.*'.format('indicators')).keys()
    to_archive = {}
    for m in monthlies:
        match = re.search(r"^indicators-((\d{4})\.\d{2})$", m)
        if match.group(1) < end_month:
            to_archive['indicators-{}'.format(match.group(1))] = 'indicators-{}'.format(match.group(2))

    # https://www.elastic.co/guide/en/elasticsearch/reference/1.4/docs-delete-by-query.html
    # http://elasticsearch-py.readthedocs.io/en/master/api.html#elasticsearch.Elasticsearch.delete_by_query
    # http://stackoverflow.com/questions/26808239/elasticsearch-python-api-delete-documents-by-query

    yearlies = []
    for c in to_archive:
        logger.info('archiving: {}'.format(c))

        i = to_archive[c]
        logger.debug(i)
        # check to see if yearly bucket exists?
        if not es.indices.exists(index=i):
            logger.debug("building: %s" % i)

            idx = Index(i)
            idx.aliases(live={})
            idx.doc_type(Indicator)
            idx.create()

            yearlies.append(i)

        # re-index
        # https://www.elastic.co/guide/en/elasticsearch/reference/current/docs-reindex.html
        q = {
            "conflicts": "proceed",
            'source': {
                'index': c,
            },
            'dest': {
                'index': to_archive[c]
            }
        }
        es.reindex(body=q, timeout='60m')

        logger.debug('flushing...')
        if es.indices.flush():
            logger.debug('removing %s' % c)
            # remove old index
            if not args.dry_run:
                es.indices.delete(index=c)

    # optimize yearlies
    for y in yearlies:
        logger.debug('optimizing: %s' % y)
        if not args.dry_run:
            es.indices.forcemerge(index=y)

        logger.debug('optimized: %s' % y)


if __name__ == "__main__":
    main()
