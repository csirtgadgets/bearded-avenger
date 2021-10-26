class Url(object):

    def __init__(self):
        pass

    def process(self, data, whitelist):
        wl = set()
        for x in whitelist:
            wl.add(x['indicator'])

        rv = []
        for x in data:
            if x['indicator'] not in wl:
                rv.append(x)

        return rv



