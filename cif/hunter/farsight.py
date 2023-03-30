import logging
from csirtg_dnsdb.client import Client
from csirtg_dnsdb.exceptions import QuotaLimit
import os
from csirtg_indicator import Indicator, InvalidIndicator
import arrow
import re

TOKEN = os.environ.get('FARSIGHT_TOKEN')
PROVIDER = os.environ.get('FARSIGHT_PROVIDER', 'dnsdb.info')
MAX_QUERY_RESULTS = os.environ.get('FARSIGHT_QUERY_MAX', 10000)

logger = logging.getLogger(__name__)


class Farsight(object):

    def __init__(self, *args, **kwargs):
        self.logger = logging.getLogger(__name__)
        self.client = Client()
        self.token = kwargs.get('token', TOKEN)
        self.is_advanced = True
        self.mtypes_supported = { 'indicators_search' }
        self.itypes_supported = { 'ipv4' }

    def _prereqs_met(self, i, **kwargs):
        if kwargs.get('mtype') not in self.mtypes_supported:
            return False

        if not self.token:
            return False

        if i.itype not in self.itypes_supported:
            return False

        if 'search' not in i.tags:
            return False

        if i.confidence and i.confidence < 9:
            return False

        if re.search(r'^(\S+)\/(\d+)$', i.indicator):
            return False

        return True

    def process(self, i, router, **kwargs):
        if not self._prereqs_met(i, **kwargs):
            return

        max = MAX_QUERY_RESULTS

        try:
            for r in self.client.search(i.indicator):
                first = arrow.get(r.get('time_first') or r.get('zone_time_first'))
                first = first.datetime
                last = arrow.get(r.get('time_last') or r.get('zone_time_last'))
                last = last.datetime

                reporttime = arrow.utcnow().datetime

                r['rrname'] = r['rrname'].rstrip('.')

                try:
                    ii = Indicator(
                        indicator=r['rdata'],
                        rdata=r['rrname'].rstrip('.'),
                        count=r['count'],
                        tags=['pdns', 'hunter'],
                        confidence=10,
                        firsttime=first,
                        lasttime=last,
                        reporttime=reporttime,
                        provider=PROVIDER,
                        tlp='amber',
                        group='everyone'
                    )
                except InvalidIndicator as e:
                    self.logger.error(e)
                    return

                router.indicators_create(ii)
                max -= 1
                if max == 0:
                    break

        except QuotaLimit:
            logger.warn('farsight quota limit reached... skipping')
        except Exception as e:
            logger.exception(e)
            return


Plugin = Farsight