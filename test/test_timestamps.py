import logging
from cif.utils.zarrow import parse_timestamp
import py.test
from pprint import pprint
import arrow

def test_timestamps():
    ts = {
            '2015-01-01': arrow.get('2015-01-01 00:00:00 Z'),
            '2015-01-01T23:59:59Z': arrow.get('2015-01-01 23:59:59Z'),
            '1367900664': arrow.get('2013-05-07T04:24:24+00:00'),
            '20160401': arrow.get('2016-04-01T00:00:00+00:00'),
            '2015-01-05T00:00:00.00Z': arrow.get('2015-01-05 00:00:00 Z'),
            '2014-01-01T23:59+04:00': arrow.get('2014-01-01T23:59:00+04:00'),
            '20130601235959': arrow.get('2013-06-01T23:59:59+00:00'),
        }

    for t in ts:
        x = parse_timestamp(t)
        print t, x
        assert x == ts[t]