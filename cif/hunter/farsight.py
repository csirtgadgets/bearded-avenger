import logging
from csirtg_dnsdb.client import Client
from csirtg_dnsdb.exceptions import QuotaLimit
import os
from csirtg_indicator import Indicator
import arrow
from pprint import pprint

TOKEN = os.environ.get('FARSIGHT_TOKEN')
PROVIDER = os.environ.get('FARSIGHT_PROVIDER', 'dnsdb.info')

logger = logging.getLogger(__name__)


class Farsight(object):

    def __init__(self, *args, **kwargs):
        self.logger = logging.getLogger(__name__)
        self.client = Client()
        self.token = kwargs.get('token', TOKEN)

    def process(self, i, router):
        if not self.token:
            return

        if i.itype != 'ipv4':
            return

        if 'search' not in i.tags:
            return

        if i.confidence and i.confidence < 9:
            return

        try:
            for r in self.client.search(i.indicator):
                first = arrow.get(r.get('time_first') or r.get('zone_time_first'))
                first = first.datetime
                last = arrow.get(r.get('time_last') or r.get('zone_time_last'))
                last = last.datetime

                reporttime = arrow.utcnow().datetime

                r['rrname'] = r['rrname'].rstrip('.')

                ii = Indicator(
                    indicator=r['rdata'],
                    rdata=r['rrname'].rstrip('.'),
                    count=r['count'],
                    tags='pdns',
                    confidence=10,
                    firsttime=first,
                    lasttime=last,
                    reporttime=reporttime,
                    provider=PROVIDER,
                    tlp='amber',
                    group='everyone'
                )

                router.indicators_create(ii)
        except QuotaLimit:
            logger.warn('farsight quota limit reached... skipping')
        except Exception as e:
            logger.exception(e)
            return


Plugin = Farsight