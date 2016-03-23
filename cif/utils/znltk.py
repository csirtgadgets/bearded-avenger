from nltk.tokenize import wordpunct_tokenize, sent_tokenize, word_tokenize
from collections import defaultdict
import logging
from cif.indicator import Indicator
from cif.utils import resolve_itype
import arrow
from pprint import pprint

KNOWN_SEPERATORS = set([',', '|', "\t", ';'])
IGNORE_SEPARATORS = set(['.', '/'])


def top_tokens(text):
    freq_dict = defaultdict(int)
    tokens = wordpunct_tokenize(text)

    for token in tokens:
        freq_dict[token] += 1

    return sorted(freq_dict, key=freq_dict.get, reverse=True)


def find_seperator(text, ignore_known=True):
    if ignore_known:
        for t in top_tokens(text):
            if t not in IGNORE_SEPARATORS:
                return t


def text_to_list(text, known_only=True):
    separator = find_seperator(text)
    t_tokens = top_tokens(text)
    top = set()
    for t in range(0, 9):
        top.add(t_tokens[t])

    if known_only:
        if separator not in KNOWN_SEPERATORS:

            pprint(top)
            raise SystemError('separator not in known list: {}'.format(separator))

    ret = []

    for l in text.split("\n"):
        if l == '':
            continue

        if l.startswith('#') or l.startswith(';'):
            continue

        cols = l.split(separator)
        cols = [x.strip() for x in cols]
        indicator = Indicator()
        for e in cols:
            if e:
                try:
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

                if e in top:
                    indicator.tags = [e]

        if indicator.itype and indicator.indicator:
            ret.append(indicator)

    return ret
