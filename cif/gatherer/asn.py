1
from cif.utils import resolve_ns
import logging
import re
from dns.rdtypes.ANY.TXT import TXT


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

            # cache it to the /24
            # 115.87.213.115
            # 0.213.87.115
            i = list(reversed(i.split('.')))
            i = '0.{}.{}.{}'.format(i[1], i[2], i[3])

            self.logger.debug('looking up: {}'.format(i))

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
                answers = resolve_ns('as{}.{}'.format(asns[0], 'asn.cymru.com'), t='TXT', timeout=15)


                ## TODO - not fixed yet
                try:
                    tmp = str(answers[0])
                except UnicodeDecodeError:
                    # requires fix latin-1 fix _escapeify to dnspython > 1.14
                    return indicator
                except IndexError:
                    from pprint import pprint
                    pprint(answers)
                    return indicator

                bits = tmp.replace('"', '').strip().split(' | ')
                if len(bits) > 4:
                    indicator.asn_desc = bits[4]

        # send back to router
        return indicator

Plugin = Asn