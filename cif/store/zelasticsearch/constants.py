import os

LIMIT = 5000
LIMIT = os.getenv('CIF_ES_LIMIT', LIMIT)

LIMIT_HARD = 500000
LIMIT_HARD = os.getenv('CIF_ES_LIMIT_HARD', LIMIT_HARD)

WINDOW_LIMIT = 250000
WINDOW_LIMIT = os.getenv('CIF_ES_WINDOW_LIMIT', WINDOW_LIMIT)

SHARDS_PER_INDEX = 1
SHARDS_PER_INDEX = os.getenv('CIF_STORE_ES_SHARDS_PER_INDEX', SHARDS_PER_INDEX)

TIMEOUT = '120'
TIMEOUT = os.getenv('CIF_ES_TIMEOUT', TIMEOUT)
TIMEOUT = '{}s'.format(TIMEOUT)

REQUEST_TIMEOUT = 60
REQUEST_TIMEOUT = os.getenv('CIF_ES_REQ_TIMEOUT', REQUEST_TIMEOUT)

UPSERT_MODE = os.getenv('CIF_STORE_ES_UPSERT_MODE', False)
if UPSERT_MODE == '1':
    UPSERT_MODE = True
else:
    UPSERT_MODE = False

PARTITION = os.getenv('CIF_STORE_ES_PARTITION', 'month')

DELETE_FILTERS = os.getenv('CIF_STORE_ES_DELETE_FILTERS', 'id, indicator, provider')
DELETE_FILTERS = DELETE_FILTERS.split(',')
DELETE_FILTERS = list(set((x.strip() for x in DELETE_FILTERS)))

UPSERT_MATCH = os.getenv('CIF_STORE_ES_UPSERT_MATCH', 'indicator, provider, confidence, tags, group, tlp, rdata, portlist, protocol')
UPSERT_MATCH = UPSERT_MATCH.split(',')
UPSERT_MATCH = set((x.strip() for x in UPSERT_MATCH))

class ReIndexError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)
