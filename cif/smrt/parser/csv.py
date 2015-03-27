from cif.smrt.parser.delim import Delim
import re


class Csv(Delim):

    def __init__(self, *args, **kwargs):
        super(Csv, self).__init__(*args, **kwargs)

        self.pattern = re.compile(',')

Plugin = Csv