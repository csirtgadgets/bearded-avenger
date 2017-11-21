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

    es = Elasticsearch(args.nodes, timeout=120, max_retries=10, retry_on_timeout=True)

    monthlies = es.indices.get_alias(index='{}-*.*'.format('cif.indicators')).keys()
    to_archive = {}
    for m in monthlies:
        match = re.search(r"^cif\.indicators-(\d{4}\.\d{2})$", m)
        if match.group(1) < end_month:
            to_archive['{}-{}'.format(args.index_prefix, match.group(1))] = '{}-{}'.format(args.index_prefix,
                                                                                        match.group(1))

    # https://www.elastic.co/guide/en/elasticsearch/reference/1.4/docs-delete-by-query.html
    # http://elasticsearch-py.readthedocs.io/en/master/api.html#elasticsearch.Elasticsearch.delete_by_query
    # http://stackoverflow.com/questions/26808239/elasticsearch-python-api-delete-documents-by-query

    pprint(to_archive)
    yearlies = ()
    for c in to_archive:
        logger.info('archiving: {}'.format(c))

        match = re.search(r"^cif\.indicators-(\d{4}).\d{2}$", c)
        i = 'cif.indicators-' + str(match.group(1))
        logger.debug(i)
        # check to see if yearly bucket exists?
        if not es.indices.exists(index=i):
            logger.debug("building: %s" % i)

            idx = Index(i)
            idx.aliases(live={})
            idx.doc_type(Indicator)
            idx.settings(max_results_window=WINDOW_LIMIT)
            idx.create()
            es.indices.flush(idx)

            yearlies.add(i)

        # aggregate index into yearly bucket
        # based on provider, tags(?), indicator
        data = ()
        for d in elasticsearch.helpers.scroll(es, scroll='60m', size=args.limit):
            i = (d['indicator'], d['provider'], data['group'], sorted(d['tags']).join(','))

            if i not in data:
                data[i].add(d)
            else:
                i = data[i]
                i['count'] += d['count']

                if i['lasttime'] < d['lasttime']:
                    i['lasttime'] = d['lasttime']

                if i['reporttime'] > d['reporttime']:
                    i['reporttime'] = d['reporttime']

                if i['firsttime'] > d['firsttime']:
                    i['firsttime'] = d['firsttime']

                if not i['message']:
                    i['message'] = []

                if d['message']:
                    i['message'].append(d['message'])

        if len(data) == 0:
            logger.info('nothing to archive...')
            continue

        actions = [{'_index': 'cif.indicators-2017', '_type': 'indicator', '_source': d} for d in data]

        # add to yearly
        if not args.dry_run:
            helpers.bulk(es, actions)

        logger.debug('flushing...')
        if es.flush():
            logger.debug('removing %s' % c)
            # remove old index
            if not args.dry_run:
                es.indices.delete(index=c, wait_for_completion=True)

    # optimize yearlies
    for y in yearlies:
        logger.debug('optimizing: %s' % y)
        if not args.dry_run:
            es.indices.optimize(index=y)

        logger.debug('optimized: %s' % y)


if __name__ == "__main__":
    main()
