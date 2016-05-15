from cif.smrt.parser import Parser
from csirtg_indicator import Indicator


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

            l = l.replace('\"', '')
            m = self.pattern.split(l)

            if len(cols):
                obs = {}
                for k, v in defaults.items():
                    obs[k] = v

                for idx, col in enumerate(cols):
                    if col is not None:
                        obs[col] = m[idx]
                obs.pop("values", None)

                try:
                    obs = Indicator(**obs)
                except NotImplementedError as e:
                    self.logger.error(e)
                    self.logger.info('skipping: {}'.format(obs['indicator']))
                else:
                    r = self.client.indicator_create(obs)
                    rv.append(r)

            if self.limit:
                self.limit -= 1

                if self.limit == 0:
                    self.logger.debug('limit reached...')
                    break

        self.logger.debug('done...')
        return rv

Plugin = Delim