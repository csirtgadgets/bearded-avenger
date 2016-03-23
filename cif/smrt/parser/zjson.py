import ujson as json
from cif.smrt.parser import Parser


class Json(Parser):

    def __init__(self, *args, **kwargs):
        super(Json, self).__init__(*args, **kwargs)

    def process(self, rule, feed, data, limit=10000000):
        data = json.loads(data)
        return data

Plugin = Json