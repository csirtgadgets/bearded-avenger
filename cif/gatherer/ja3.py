import requests
import ujson as json
import logging
import os

#Set CIF_GATHERERS_JA3_ENABLED=0 to disable this gatherer
ENABLE_JA3 = os.environ.get('CIF_GATHERERS_JA3_ENABLED')


class Ja3(object):

    def __init__(self, *args, **kwargs):
        self.logger = logging.getLogger(__name__)
        if ENABLE_JA3 == '0':
            self.enabled = False
        else:
            self.enabled = True

    def _resolve(self, data):
        try:
            request = requests.get('https://ja3er.com/search/{}'.format(data), timeout=1)
        except Exception as e:
            self.logger.debug(e)
            return
        return json.loads(request.text)

    def process(self, indicator):
        if not self.enabled:
            self.logger.debug('self.enabled is set to {}'.format(self.enabled))
            return indicator

        #if indicator isn't a md5 hash with ja3 tag, or it's already coming from the ja3er.com provider (bc ja3 smrt rule adds desc), exit
        if (not indicator.itype == 'md5') or (indicator.provider == 'ja3er.com') or ('ja3' not in indicator.tags):
            return indicator

        #if indicator has a description do not attempt to enrich further
        if indicator.description:
            return indicator

        try:
            i = str(indicator.indicator)

            ua = self._resolve(i)
            if not ua or len(ua) == 0:
                return indicator
        except Exception as e:
            self.logger.error('Gatherer [ja3]: Error on indicator {} - {}'.format(indicator, e))

        for each in ua:
            self.logger.debug(each)
            indicator.lasttime = each.get('Last_seen')
            indicator.description = each.get('User-Agent')

        return indicator


Plugin = Ja3
