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
from cif.constants import VERSION
from cifsdk.utils import setup_logging
from pprint import pprint
import os
from faker import Faker
import random
import arrow
from elasticsearch_dsl import Index
from elasticsearch import helpers
import elasticsearch.exceptions
from elasticsearch_dsl.connections import connections
from cif.store.zelasticsearch.schema import Indicator
from cif.store.zelasticsearch.helpers import expand_ip_idx

MONTHS = 6
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

    args = p.parse_args()
    setup_logging(args)
    logger = logging.getLogger(__name__)

    # es = Elasticsearch(args.nodes, timeout=120, max_retries=10, retry_on_timeout=True)
    connections.create_connection(hosts=args.nodes)
    es = connections.get_connection()

    fake = Faker()
    ips = [fake.ipv4() for n in range(1,25)]
    for m in range(1, int(args.months)):
        data = {}

        if m < 10:
            m = "0%s" % m

        month = 'indicators-2017.%s' % m
        data[month] = []
        for n in range(1, int(args.limit)):
            day = random.randint(1, 28) # avoid feb, etc..
            if day < 10:
                day = "0%i" % day

            ts = fake.time(pattern="%H:%M:%S")

            ts = ('2017-%s-%sT%s' % (str(m), str(day), str(ts)))
            ts = '%sZ' % ts
            # create an indicator
            i = {
                'indicator': random.choice(ips),
                'itype': 'ipv4',
                'tags': random.choices(['scanner', 'botnet', 'malware', 'suspicious', 'hijacked'], k=2),
                'description': fake.name(),
                'count': 1, #random.randint(1, 66),
                'confidence': random.randint(1, 10),
                'reporttime': ts,
                'lasttime': ts,
                'firsttime': ts,
                'provider': fake.words(1)[0],
                'tlp': random.choices(['red', 'amber', 'green'], k=1),
                'cc': fake.country_code(),
                'asn': random.randint(1, 65535),
                'group': 'everyone',
            }
            # drop it in the bucket
            data[month].append(i)
            if n % 10000 == 0:
                logger.info('%i generated' % n)

            try:
                index = Index(month)
                index.aliases(live={})
                index.doc_type(Indicator)
                index.create()
                es.indices.flush(month)
            except elasticsearch.exceptions.RequestError:
                pass

            actions = []

        for i in data[month]:
            expand_ip_idx(i)

            i = {
                '_index': month,
                '_type': 'indicator',
                '_source': i
            }

            actions.append(i)

        print("sending...")
        helpers.bulk(es, actions, index=month)
        print("sent %i actions" % (len(actions) + 1))



    # connections.create_connection(hosts=args.nodes)
    # es = connections.get_connection()
    #
    # for bucket in data:
    #     try:
    #         index = Index(bucket)
    #         index.aliases(live={})
    #         index.doc_type(Indicator)
    #         index.create()
    #         es.indices.flush(bucket)
    #     except elasticsearch.exceptions.RequestError:
    #         pass
    #
    #     actions = []
    #
    #     for i in data[bucket]:
    #         expand_ip_idx(i)
    #
    #         i = {
    #             '_index': bucket,
    #             '_type': 'indicator',
    #             '_source': i
    #         }
    #
    #         actions.append(i)
    #
    #     print("sending...")
    #     helpers.bulk(es, actions, index=bucket)
    #     print("sent %i actions" % (len(actions) + 1))


if __name__ == "__main__":
    main()
