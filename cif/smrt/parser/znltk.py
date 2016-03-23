from cif.smrt.parser import Parser
from cif.utils import resolve_itype, setup_logging, get_argument_parser
from nltk.tokenize import wordpunct_tokenize
from collections import defaultdict
from pprint import pprint
import logging
from cif.indicator import Indicator
import arrow


class Nltk_(Parser):

    def __init__(self, *args, **kwargs):
        super(Nltk_, self).__init__(*args, **kwargs)

        self.logger = logging.getLogger(__name__)

    def _find_seperator(self, text):
        freq_dict = defaultdict(int)
        tokens = wordpunct_tokenize(text)

        for token in tokens:
            freq_dict[token] += 1

        top = sorted(freq_dict, key=freq_dict.get, reverse=True)
        self.logger.debug(top)
        self.top = set()
        for t in range(0, 9):
            self.top.add(top[t])
        return top[0]

    def process(self, rule, feed, data):
        sep = self._find_seperator(data)
        ret = []

        for l in data.split("\n"):
            if l == '':
                continue

            if l.startswith('#'):
                continue

            cols = l.split(sep)
            cols = [x.strip() for x in cols]
            self.logger.debug(cols)
            indicator = Indicator()
            for e in cols:
                if e:
                    try:
                        self.logger.debug(e)
                        i = resolve_itype(e)
                        if i:
                            indicator.indicator = e
                            indicator.itype = i
                    except NotImplementedError:
                        pass

                    try:
                        ts = arrow.get(e)
                        if ts:
                            indicator.lasttime = ts.datetime
                    except (arrow.parser.ParserError, UnicodeDecodeError):
                        pass

                    if e in self.top:
                        indicator.tags = [e]

            if not indicator.itype and indicator.indicator and indicator.lasttime and indicator.top:
                    self.logger.debug('skipping {}'.l)
            else:
                self.logger.info('submitting: {}'.format(indicator))
                ret.append(indicator)

        return ret


Plugin = Nltk_

text = """
701          |  UUNET - MCI Communications Ser  |      68.135.40.6  |  2015-12-07 17:42:20  |  vncprobe
701          |  UUNET - MCI Communications Ser  |   71.178.253.108  |  2015-12-07 17:26:28  |  vncprobe
760          |  University of Vienna, Austria,  |   131.130.69.196  |  2015-12-08 07:25:40  |  vncprobe
3215         |  AS3215 Orange S.A.,FR           |     80.13.221.76  |  2015-12-08 10:36:56  |  vncprobe
3462         |  HINET Data Communication Busin  |     114.32.32.66  |  2015-12-03 04:02:22  |  vncprobe
3790         |  RADIOGRAFICA COSTARRICENSE,CR   |     190.10.8.226  |  2015-12-06 19:38:31  |  vncprobe
3790         |  RADIOGRAFICA COSTARRICENSE,CR   |     190.10.9.246  |  2015-12-06 21:09:17  |  vncprobe
"""

def main():
    p = get_argument_parser()

    args = p.parse_args()
    setup_logging(args)
    n = Nltk_(None, None, None, None)
    x = n.process(None, None, text)

    pprint(x)


if __name__ == '__main__':
    main()