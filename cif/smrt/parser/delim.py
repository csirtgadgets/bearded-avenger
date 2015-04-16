from cif.smrt.parser import Parser


class Delim(Parser):

    def __init__(self, *args, **kwargs):
        super(Delim, self).__init__(*args, **kwargs)

    def process(self):
        defaults = self._defaults()
        cols = defaults['values']

        rv = []
        for l in self.fetcher.process():
            if l == '' or self.is_comment(l):
                continue

            m = self.pattern.split(l)
            if len(cols):
                obs = {}
                for k, v in defaults.iteritems():
                    obs[k] = v

                for idx, col in enumerate(cols):
                    if col is not None:
                        obs[col] = m[idx]
                obs.pop("values", None)
                r = self.client.submit(**obs)
                rv.append(r)
            self.limit -= 1
            if self.limit == 0:
                break

        return rv

Plugin = Delim