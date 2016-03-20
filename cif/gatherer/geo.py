

import logging
import os

DB_PATH=''


class Geo(object):

    def __init__(self, path=DB_PATH, *args, **kv):
        self.logger = logging.getLogger(__name__)

        self.path = path

        # configure reader here..

    def process(self, indicator):
        if not os.path.isfile(self.path):
            return False

        # https://github.com/csirtgadgets/massive-octo-spice/blob/develop/src/lib/CIF/Meta/GeoIP.pm
        # https://geoip2.readthedocs.org/en/latest/
        # https://github.com/maxmind/GeoIP2-python
        # domains???
        pass


Plugin = Geo