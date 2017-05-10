
def tag_contains_whitelist(data):
    for d in data:
        if d == 'whitelist':
            return True


class Sha256(object):

    def __init__(self):
        pass

    def process(self, data, whitelist):
        wl = set()
        for x in whitelist:
            wl.add(x['indicator'])

        rv = []
        for x in data:
            if tag_contains_whitelist(x['tags']):
                continue

            if x['indicator'] not in wl:
                rv.append(x)

        return rv



