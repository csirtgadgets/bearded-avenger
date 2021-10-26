import pytricia
import logging

PERM_WHITELIST = [
    ## TODO -- more
    # http://www.iana.org/assignments/ipv6-multicast-addresses/ipv6-multicast-addresses.xhtml
    # v6
    'FF01:0:0:0:0:0:0:1',
    'FF01:0:0:0:0:0:0:2',
]


class Ipv6(object):

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        pass

    def process(self, data, whitelist=[]):
        wl = pytricia.PyTricia()

        [wl.insert(x, True) for x in PERM_WHITELIST]

        [wl.insert(str(y['indicator']), True) for y in whitelist]

        rv = []
        for y in data:
            if str(y['indicator']) not in wl:
                rv.append(y)

        return rv




