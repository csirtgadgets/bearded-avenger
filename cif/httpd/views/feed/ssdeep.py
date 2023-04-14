class Ssdeep(object):

    def __init__(self):
        pass

    def process(self, data, allowlist):
        allowed = set()
        for x in allowlist:
            allowed.add(x['indicator'])

        rv = []
        for x in data:
            if x['indicator'] not in allowed:
                rv.append(x)

        return rv
