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
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from elasticsearch import helpers
import re
from cifsdk import VERSION
from cifsdk.utils import setup_logging
from pprint import pprint

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

    args = p.parse_args()
    setup_logging(args)
    logger = logging.getLogger(__name__)

    end_month = (datetime.today() - relativedelta(months=int(args.months)))
    end_month = end_month.strftime('%Y.%m')

    logger.info('month: {}'.format(end_month))

    es = Elasticsearch(args.nodes, timeout=120, max_retries=10, retry_on_timeout=True)

    monthlies = es.indices.get_aliases(index='{}-*.*'.format(args.index_prefix)).keys()
    to_archive = {}
    for m in monthlies:
        match = re.search(r"^cif\.indicators-(\d{4}\.\d{2})$", m)
        if match.group(1) < end_month:
            to_archive['{}-{}'.format(args.index_prefix, match.group(1))] = '{}-{}'.format(args.index_prefix,
                                                                                        match.group(1))

    # https://www.elastic.co/guide/en/elasticsearch/reference/1.4/docs-delete-by-query.html
    # http://elasticsearch-py.readthedocs.io/en/master/api.html#elasticsearch.Elasticsearch.delete_by_query
    # http://stackoverflow.com/questions/26808239/elasticsearch-python-api-delete-documents-by-query

    yearlies = ()
    for c in to_archive:
        logger.info('archiving: {}'.format(c))
        if args.dry_run:
            continue

        i = 'cif.indicators-2017'
        # check to see if yearly bucket exists?
        if not es.indices.exists(index='cif.indicators-2017'):
            logger.debug("building: %s" % i)
            from cif.store.zelasticsearch.indicator import Index, Indicator
            from cif.store.zelasticsearch.constants import WINDOW_LIMIT
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
        for d in elasticsearch.helpers.scroll(es, scroll='60m', size=5000):
            i = d['indicator']
            if d['indicator'] not in data:
                data[i] = d
                continue

            i = data[i]
            i['count'] += 1
            if i['lasttime'] < d['lasttime']:
                i['lasttime'] = d['lasttime']

            if i['reporttime'] > d['reporttime']:
                i['reporttime'] = d['reporttime']

            if i['firsttime'] > d['firsttime']:
                i['firsttime'] = d['firsttime']

            # tags?

        # remove index
        es.indices.delete(index=c, wait_for_completion=True)

    # optimize yearlies
    for y in yearlies:
        es.indices.optimize(index=y)


if __name__ == "__main__":
    main()
