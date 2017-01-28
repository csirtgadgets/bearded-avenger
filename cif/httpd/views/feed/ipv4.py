
import pytricia
import logging
import ipaddress
import sys

from pprint import pprint

PERM_WHITELIST = [
    "0.0.0.0/8",
    "10.0.0.0/8",
    "127.0.0.0/8",
    "192.168.0.0/16",
    "169.254.0.0/16",
    "192.0.2.0/24",
    "224.0.0.0/4",
    "240.0.0.0/5",
    "248.0.0.0/5",
]

LARGEST_PREFIX = '8'


def tag_contains_whitelist(data):
    for d in data:
        if d == 'whitelist':
            return True


def _normalize(i):
    bits = i.split('.')

    rv = []
    for b in bits:
        if len(b) > 1 and b.startswith('0') and not b.startswith('0/'):
            b = b[1:]
        rv.append(b)

    return '.'.join(rv)


class Ipv4(object):

    def __init__(self):
        pass

    # https://github.com/jsommers/pytricia
    def process(self, data, whitelist=[]):
        wl = pytricia.PyTricia()
        for x in PERM_WHITELIST:
            wl[x] = True

        for y in whitelist:
            y = str(_normalize(y['indicator']))
            if '/' not in y: # weird bug work-around it'll insert 172.16.1.60 with a /0 at the end??
                y = '{}/32'.format(y)
            wl[y] = True

        # this could be done with generators...
        rv = []

        for y in data:
            if tag_contains_whitelist(y['tags']):
                continue

            y['indicator'] = _normalize(y['indicator'])
            try:
                if sys.version_info.major < 3:
                    ipaddress.ip_network(unicode(y['indicator']))
                else:
                    ipaddress.ip_network(y['indicator'])
                if str(y['indicator']) not in wl:
                    rv.append(y)
            except ValueError as e:
                print(e)
                print('skipping invalid address: %s' % y['indicator'])

        return rv




