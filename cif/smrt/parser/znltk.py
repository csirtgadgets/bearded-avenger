from cif.smrt.parser import Parser
from pprint import pprint
import logging
from cif.utils.znltk import text_to_list


class Nltk_(Parser):

    def __init__(self, *args, **kwargs):
        super(Nltk_, self).__init__(*args, **kwargs)

        self.logger = logging.getLogger(__name__)

    def process(self, rule, feed, data):
        ret = []

        try:
            ret = text_to_list(data)
        except Exception as e:
            self.logger.error(e)
            raise e

        return ret
