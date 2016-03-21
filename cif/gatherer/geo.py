

import logging
import os
import geoip2.database
from pprint import pprint

DB_PATH = '/usr/local/share/GeoIP'
DB_FILE = 'GeoLite2-City.mmdb'


class Geo(object):

    def __init__(self, path=DB_PATH, db=DB_FILE):
        self.logger = logging.getLogger(__name__)

        self.db = None
        if os.path.isfile(os.path.join(path, db)):
            self.db = geoip2.database.Reader(os.path.join(path, db))

    def process(self, indicator):
        if not self.db:
            return None

        if indicator.itype == 'ipv4':
            # https://github.com/csirtgadgets/massive-octo-spice/blob/develop/src/lib/CIF/Meta/GeoIP.pm
            # https://geoip2.readthedocs.org/en/latest/
            # https://github.com/maxmind/GeoIP2-python
            # domains???
            r = self.db.city(indicator.indicator)
            if r.country.iso_code:
                indicator.cc = r.country.iso_code

            if r.city.name:
                indicator.city = r.city.name

            print(indicator)

Plugin = Geo


def main():
    from cif.indicator import Indicator
    i = Indicator(indicator='128.101.101.101')

    x = Geo(path='./')
    x.process(i)

if __name__ == "__main__":
    main()