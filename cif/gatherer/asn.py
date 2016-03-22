
from cif.utils import resolve_ns
import logging


class Asn(object):

    def __init__(self, *args, **kv):
        self.logger = logging.getLogger(__name__)

    def process(self, indicator):
        if indicator.itype == 'ipv4':
            i = '.'.join(reversed(indicator.indicator.split('.')))

            answers = resolve_ns('{}.{}'.format(i, 'origin.asn.cymru.com'), t='TXT')

            if len(answers) > 0:
                # Separate fields and order by netmask length
                # 23028 | 216.90.108.0/24 | US | arin | 1998-09-25
                # 701 1239 3549 3561 7132 | 216.90.108.0/24 | US | arin | 1998-09-25

                # i.asn_desc ????
                self.logger.debug(answers[0])
                bits = str(answers[0]).replace('"', '').strip().split(' | ')
                asns = bits[0].split(' ')

                for a in asns:
                    indicator.asn = a
                    indicator.prefix = bits[1]
                    indicator.cc = bits[2]
                    indicator.rir = bits[3]

        # send back to router
        return indicator

Plugin = Asn