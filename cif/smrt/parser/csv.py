from cif.smrt.parser.delim import Delim


class CSV(Delim):

    def __init__(self, *args, **kwargs):
        super(CSV, self).__init__(*args, **kwargs)
