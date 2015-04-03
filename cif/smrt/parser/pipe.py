from cif.smrt.parser.delim import Delim
import re


class Pipe(Delim):

    def __init__(self, *args, **kwargs):
        super(Pipe, self).__init__(*args, **kwargs)

        self.pattern = re.compile('\||\s+\|\s+')

        # page 194
        # mylist = []
        # header = file.readline().strip().split("|")
        # for l in file:
        #     l = l.strip().split("|")
        #     map = zip(header, l)
        #     mylist.append(dict(map))



Plugin = Pipe