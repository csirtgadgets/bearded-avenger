
from cif.utils import resolve_ns
import logging
import re


class Asn(object):

    def __init__(self, *args, **kv):
        self.logger = logging.getLogger(__name__)

    def _resolve(self, data):
        return resolve_ns('{}.{}'.format(data, 'origin.asn.cymru.com'), t='TXT')

    def process(self, indicator):
        if indicator.itype == 'ipv4' and not indicator.is_private():
            i = str(indicator.indicator)
            match = re.search('^(\S+)\/\d+$', i)
            if match:
                i = match.group(1)

            i = '.'.join(reversed(i.split('.')))

            answers = self._resolve(i)

            if len(answers) > 0:
                # Separate fields and order by netmask length
                # 23028 | 216.90.108.0/24 | US | arin | 1998-09-25
                # 701 1239 3549 3561 7132 | 216.90.108.0/24 | US | arin | 1998-09-25

                # i.asn_desc ????
                self.logger.debug(answers[0])
                bits = str(answers[0]).replace('"', '').strip().split(' | ')
                asns = bits[0].split(' ')

                indicator.asn = asns[0]
                indicator.prefix = bits[1]
                indicator.cc = bits[2]
                indicator.rir = bits[3]
                answers = resolve_ns('as{}.{}'.format(asns[0], 'asn.cymru.com'), t='TXT')


                ## TODO - not fixed yet
                try:
                    tmp = str(answers[0])
                except UnicodeDecodeError:
                    tmp = bytes(answers[0], 'latin-1')
                    tmp = str(tmp)

                bits = tmp.replace('"', '').strip().split(' | ')
                if len(bits) > 4:
                    indicator.asn_desc = bits[4]

        # send back to router
        return indicator

Plugin = Asn