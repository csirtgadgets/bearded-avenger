

import logging
import os
import geoip2.database
from geoip2.errors import AddressNotFoundError
import re
from pprint import pprint

DB_SEARCH_PATHS = [
    './',
    '/usr/local/share/GeoIP'
]

DB_FILE = 'GeoLite2-City.mmdb'
DB_PATH = os.environ.get('CIF_GEO_PATH')


class Geo(object):

    def __init__(self, path=DB_SEARCH_PATHS, db=DB_FILE):
        self.logger = logging.getLogger(__name__)

        self.db = None
        if DB_PATH:
            self.db = geoip2.database.Reader(os.path.join(DB_PATH, db))
        else:
            for p in DB_SEARCH_PATHS:
                if os.path.isfile(os.path.join(p, db)):
                    self.db = geoip2.database.Reader(os.path.join(p, db))
                    break

    def _resolve(self, indicator):
        if self.db:
            g = self.db.city(str(indicator.indicator))

            if g.country.iso_code:
                indicator.cc = g.country.iso_code

            if g.city.name:
                indicator.city = g.city.name

            if g.location.longitude:
                indicator.longitude = g.location.longitude

            if g.location.latitude:
                indicator.longitude = g.location.latitude

            if g.location.time_zone:
                indicator.timezone = g.location.time_zone

    def process(self, indicator):
        if (indicator.itype == 'ipv4' or indicator.itype == 'ipv6') and not indicator.is_private():
            # https://geoip2.readthedocs.org/en/latest/
            i = str(indicator.indicator)
            self.logger.debug(i)
            match = re.search('^(\S+)\/\d+$', i)
            tmp = indicator.indicator
            if match:
                i = match.group(1)
                indicator.indicator = i

            self.logger.debug('looking up: %s' % i)

            try:
                self._resolve(indicator)
                indicator.indicator = tmp
            except AddressNotFoundError as e:
                self.logger.warn(e)

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        if self.db:
            self.db.close()


Plugin = Geo