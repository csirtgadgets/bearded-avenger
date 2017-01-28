
from pprint import pprint

PERM_WHITELIST = [
    'google.com',
    'yahoo.com',
    'facebook.com',
    'youtube.com',
    'netflix.com',
    'baidu.com',
    'wikipedia.org',
    'twitter.com',
    'qq.com',
    'taobao.com',
    'amazon.com',
    'live.com',
    'bing.com',
    'wordpress.com',
    'msn.com',
    'update.symantec.com',
]


class Fqdn(object):

    def __init__(self):
        self.wl = set()
        for w in PERM_WHITELIST:
            self.wl.add(w)

    def match_whitelist(self, wl, d):
        bits = d.split('.')
        bits2 = list(bits)

        for i, b in enumerate(bits2):
            if '.'.join(bits) in wl:
                return True
            bits.pop(0)

    # https://github.com/jsommers/pytricia
    def process(self, data, whitelist):

        wl = self.wl

        for w in whitelist:
            wl.add(w['indicator'])

        rv = []
        for x in data:
            if not self.match_whitelist(wl, x['indicator']):
                rv.append(x)

        return rv



