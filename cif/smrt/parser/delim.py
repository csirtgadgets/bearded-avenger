from cif.smrt.parser import Parser

from pprint import pprint
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
                self.logger.debug(str(obs))
                rv.append(r)

            if self.limit:
                self.limit -= 1

                if self.limit == 0:
                    self.logger.debug('limit reached...')
                    break

        self.logger.debug('done...')
        return rv

Plugin = Delim