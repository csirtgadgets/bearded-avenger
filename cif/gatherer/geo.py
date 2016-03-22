

import logging
import os
import geoip2.database
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

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        if self.db:
            self.db.close()

    def process(self, indicator):
        if not self.db:
            return indicator

        if indicator.itype == 'ipv4' or indicator.itype == 'ipv6':
            # https://geoip2.readthedocs.org/en/latest/
            r = self.db.city(indicator.indicator)
            if r.country.iso_code:
                indicator.cc = r.country.iso_code

            if r.city.name:
                indicator.city = r.city.name

            if r.location.longitude:
                indicator.longitude = r.location.longitude

            if r.location.latitude:
                indicator.longitude = r.location.latitude

            if r.location.time_zone:
                indicator.timezone = r.location.time_zone


        return indicator

Plugin = Geo