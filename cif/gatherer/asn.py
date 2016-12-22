
from cif.utils import resolve_ns
import logging
import re
import os
from cif.asn_client import ASNClient

ASN_FAST = os.environ.get('CIF_GATHERER_ASN_FAST')


class Asn(object):

    def __init__(self, *args, **kv):
        self.logger = logging.getLogger(__name__)
        self.asn_fast = None
        if ASN_FAST:
            self.asn_fast = ASNClient(ASN_FAST)

    def _resolve(self, data):
        return resolve_ns('{}.{}'.format(data, 'origin.asn.cymru.com'), t='TXT')

    def _resolve_fast(self, data):
        return self.asn_fast.lookup(data)

    def process(self, indicator):
        if indicator.is_private():
            return

        # TODO ipv6
        if indicator.itype != 'ipv4':
            return

        i = str(indicator.indicator)
        match = re.search('^(\S+)\/\d+$', i)
        if match:
            i = match.group(1)

        if ASN_FAST:
            bits = self._resolve_fast(indicator.indicator)
            for k in bits:
                if bits[k] == 'NA':
                    bits[k] = False

            if bits['asn']:
                bits['asn'] = str(bits['asn'])

            indicator.asn = bits['asn']
            indicator.prefix = bits['prefix']
            indicator.asn_desc = bits['owner']
            indicator.cc = bits['cc']

            return indicator

        # cache it to the /24
        # 115.87.213.115
        # 0.213.87.115
        i = list(reversed(i.split('.')))
        i = '0.{}.{}.{}'.format(i[1], i[2], i[3])

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

            try:
                tmp = str(answers[0])
            except UnicodeDecodeError as e:
                # requires fix latin-1 fix _escapeify to dnspython > 1.14
                self.logger.debug(e)
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