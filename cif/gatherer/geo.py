

import logging
import os
import geoip2.database
import pygeoip
from geoip2.errors import AddressNotFoundError
import re
from csirtg_indicator import Indicator
from cif.constants import PYVERSION
from pprint import pprint
if PYVERSION > 2:
    from urllib.parse import urlparse
else:
    from urlparse import urlparse
import socket

DB_SEARCH_PATHS = [
    './',
    '/usr/share/GeoIP',
    '/usr/local/share/GeoIP'
]

ENABLE_FQDN = os.getenv('CIF_GATHERER_GEO_FQDN')
DB_FILE = 'GeoLite2-City.mmdb'
DB_PATH = os.environ.get('CIF_GEO_PATH')

#ASN_DB_PATH = 'GeoIPASNum.dat'
#ASN_DB_PATH2 = 'GeoLiteASNum.dat'
#CITY_DB_PATH = 'GeoLiteCity.dat'
#CITY_V6_DB_PATH = 'GeoLiteCityv6.dat'


class Geo(object):
    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        if self.db:
            self.db.close()

    def __init__(self, path=DB_SEARCH_PATHS, db=DB_FILE):
        self.logger = logging.getLogger(__name__)

        self.db = None
        self.asn_db = None

        if DB_PATH:
            self.db = geoip2.database.Reader(os.path.join(DB_PATH, db))
        else:
            for p in DB_SEARCH_PATHS:
                if os.path.isfile(os.path.join(p, db)):
                    self.db = geoip2.database.Reader(os.path.join(p, db))
                    break

    def _lookup_ip(self, host):
        try:
            host = socket.gethostbyname(host)
        except:
            host = None

        return host

    def _ip_to_prefix(self, i):
        i = list(i.split('.'))
        i = '{}.{}.{}.0'.format(i[0], i[1], i[2])
        return str(i)

    def _resolve(self, indicator):
        if not self.db:
            return

        i = indicator.indicator
        if indicator.itype in ['url', 'fqdn']:
            if ENABLE_FQDN in ['0', 0, False, None]:
                return

            if indicator.itype == 'url':
                u = urlparse(i)
                i = u.hostname

            i = self._lookup_ip(i)
            if not i:
                return

            if not indicator.rdata:
                indicator.rdata = i

        if indicator.itype == 'ipv4':
            try:
                i = self._ip_to_prefix(i)
            except IndexError:
                self.logger.error('unable to determine geo for %s' % indicator.indicator)
                return

        g = self.db.city(i)

        if g.country.iso_code:
            indicator.cc = g.country.iso_code

        if g.city.name:
            indicator.city = g.city.name

        if g.location.longitude:
            indicator.longitude = g.location.longitude

        if g.location.latitude:
            indicator.latitude = g.location.latitude
            
        if g.location.latitude and g.location.longitude:
            indicator.location = [g.location.longitude, g.location.latitude]

        if g.location.time_zone:
            indicator.timezone = g.location.time_zone

        # g = self.db.record_by_addr(i)

        # if g and g.region_code:
        #     indicator.region = g['region_code']

        try:
            indicator.region = g.subdivisions[0].names['en']
        except Exception:
            pass

        if not self.asn_db:
            return

        g = self.asn_db.asn_by_addr(i)
        if g:
            m = re.match('^AS(\d+)\s([^.]+)', g)
            if m:
                indicator.asn = m.group(1)
                indicator.asn_desc = m.group(2)

    def process(self, indicator):
        if indicator.itype not in ['ipv4', 'ipv6', 'fqdn', 'url']:
            return indicator

        if indicator.is_private():
            return indicator

        # https://geoip2.readthedocs.org/en/latest/
        i = str(indicator.indicator)
        tmp = indicator.indicator

        if indicator.itype in ['ipv4', 'ipv6']:
            match = re.search('^(\S+)\/\d+$', i)
            if match:
                indicator.indicator = match.group(1)

        try:
            if indicator.indicator:
                self._resolve(indicator)
            indicator.indicator = tmp
        except AddressNotFoundError as e:
            self.logger.warn(e)
            indicator.indicator = tmp

        return indicator

Plugin = Geo

import sys


def main():
    g = Geo()
    i = sys.argv[1]

    i = Indicator(i)
    i = g.process(i)

    pprint(i)


if __name__ == "__main__":
    main()
