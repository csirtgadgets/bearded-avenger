import arrow
import datetime
import re
from pprint import pprint


def parse_timestamp(ts):
    try:
        t = arrow.get(ts)
        if t.year < 1980:
            if type(ts) == datetime.datetime:
                ts = str(ts)
            if len(ts) == 8:
                ts = '{}T00:00:00Z'.format(ts)
                t = arrow.get(ts, 'YYYYMMDDTHH:mm:ss')

            if t.year < 1980:
                raise RuntimeError('invalid timestamp: %s' % ts)

        return t
    except ValueError as e:
        print(len(ts))
        if len(ts) == 14:
            match = re.search('^(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})$', ts)
            if match:
                ts = '{}-{}-{}T{}:{}:{}Z'.format(match.group(1), match.group(2), match.group(3), match.group(4),
                                                 match.group(5), match.group(6))
                t = arrow.get(ts, 'YYYY-MM-DDTHH:mm:ss')
                return t
            else:
                raise RuntimeError('Invalid Timestamp: %s' % ts)
        else:
            raise RuntimeError('Invalid Timestamp: %s' % ts)
    else:
        raise RuntimeError('Invalid Timestamp: %s' % ts)