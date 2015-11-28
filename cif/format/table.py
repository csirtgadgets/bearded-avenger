from prettytable import PrettyTable
from pprint import pprint
from cif.format import COLUMNS, MAX_FIELD_SIZE


class Table(object):

    def __init__(self, data, cols=COLUMNS, max_field_size=MAX_FIELD_SIZE):
        self.cols = cols
        self.max_field_size = max_field_size
        self.data = data

    def __repr__(self):
        t = PrettyTable(self.cols)
        t.align['provider'] = 'l'
        for obs in self.data:
            r = []
            for c in self.cols:
                y = obs.get(c, '')
                if type(y) is list:
                    y = ','.join(y)

                # http://stackoverflow.com/questions/3224268/python-unicode-encode-error
                # http://stackoverflow.com/questions/19833440/unicodeencodeerror-ascii-codec-cant-encode-character-u-xe9-in-position-7
                try:
                    if type(y) is unicode:
                        y = y.encode('ascii', 'ignore')
                except NameError:
                    # python3
                    pass

                y = str(y)
                y = (y[:self.max_field_size] + '..') if len(y) > self.max_field_size else y
                r.append(y)
            t.add_row(r)
        return str(t)