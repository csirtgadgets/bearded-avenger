from cif.smrt.parser.delim import Delim
import re


class Pipe(Delim):

    def __init__(self, *args, **kwargs):
        super(Pipe, self).__init__(*args, **kwargs)

        self.pattern = re.compile('\||\s+\|\s+')

Plugin = Pipe