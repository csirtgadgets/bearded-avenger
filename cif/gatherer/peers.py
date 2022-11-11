
from cif.utils import resolve_ns
import logging
import os
import re

ENABLE_PEERS = os.environ.get('CIF_GATHERERS_PEERS_ENABLED')


class Peer(object):

    def __init__(self, *args, **kwargs):
        self.logger = logging.getLogger(__name__)
        self.enabled = kwargs.get('enabled', os.environ.get('CIF_GATHERERS_PEERS_ENABLED'))

    def _resolve(self, data):
        return resolve_ns('{}.{}'.format(data, 'peer.asn.cymru.com', timeout=15), t='TXT')

    def process(self, indicator):
        if not self.enabled:
            return indicator

        if not indicator.itype == 'ipv4':
            return indicator

        if indicator.is_private():
            return indicator

        i = str(indicator.indicator)
        match = re.search(r'^(\S+)\/\d+$', i)
        if match:
            i = match.group(1)

        # cache it to the /24
        i = list(reversed(i.split('.')))
        i = '0.{}.{}.{}'.format(i[1], i[2], i[3])

        answers = self._resolve(i)
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