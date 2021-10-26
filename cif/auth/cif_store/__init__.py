import logging
import os

from cif.auth.plugin import Auth
from cif.store import Store
import traceback

STORE_DEFAULT = os.environ.get('CIF_STORE_STORE', 'sqlite')
STORE_NODES = os.getenv('CIF_STORE_NODES')

TRACE = os.environ.get('CIF_AUTH_CIFSTORE_TRACE', True)

logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)

if TRACE:
    logger.setLevel(logging.DEBUG)

class CifStore(Auth):

    name = 'cif_store'

    def __init__(self, **kwargs):
        self.store = Store(store_type=STORE_DEFAULT, nodes=STORE_NODES)
        self.store._load_plugin(store_type=STORE_DEFAULT, nodes=STORE_NODES)

    def handle_token_search(self, token, **kwargs):
        return self.store.store.tokens.auth_search({'token': token})    

Plugin = CifStore
