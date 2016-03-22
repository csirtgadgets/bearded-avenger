
from cif.utils import resolve_ns
import logging


class Peer(object):

    def __init__(self, *args, **kv):
        self.logger = logging.getLogger(__name__)

    def process(self, indicator):
        if indicator.itype == 'ipv4':
            i = '.'.join(reversed(indicator.indicator.split('.')))
            answers = resolve_ns('{}.{}'.format(i, 'peer.asn.cymru.com'), t='TXT')
            if len(answers) > 0:
                if not indicator.peers:
                    indicator.peers = []
                # Separate fields and order by netmask length
                # 23028 | 216.90.108.0/24 | US | arin | 1998-09-25
                # 701 1239 3549 3561 7132 | 216.90.108.0/24 | US | arin | 1998-09-25
                for p in answers:
                    self.logger.debug(p)
                    bits = str(p).replace('"', '').strip().split(' | ')
                    asn = bits[0]
                    prefix = bits[1]
                    cc = bits[2]
                    rir = bits[3]
                    asns = asn.split(' ')
                    for a in asns:
                        indicator.peers.append({
                            'asn': a,
                            'prefix': prefix,
                            'cc': cc,
                            'rir': rir
                        })

        return indicator

Plugin = Peer