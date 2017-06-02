import os.path
from cifsdk.constants import RUNTIME_PATH
import sys

PYVERSION = 2
if sys.version_info > (3,):
    PYVERSION = 3

from ._version import get_versions
VERSION = get_versions()['version']
del get_versions

TOKEN_LENGTH = 40

ROUTER_ADDR = "ipc://{}".format(os.path.join(RUNTIME_PATH, 'router.ipc'))
ROUTER_ADDR = os.environ.get('CIF_ROUTER_ADDR', ROUTER_ADDR)

ROUTER_LOCAL_ADDR = "ipc://{}".format(os.path.join(RUNTIME_PATH, 'router_local.ipc'))
ROUTER_LOCAL_ADDR = os.environ.get('CIF_ROUTER_ADDR', ROUTER_LOCAL_ADDR)

STORE_ADDR = 'ipc://{}'.format(os.path.join(RUNTIME_PATH, 'store.ipc'))
STORE_ADDR = os.environ.get('CIF_STORE_ADDR', STORE_ADDR)

CTRL_ADDR = 'ipc://{}'.format(os.path.join(RUNTIME_PATH, 'ctrl.ipc'))
CTRL_ADDR = os.environ.get('CIF_CTRL_ADDR', CTRL_ADDR)

HUNTER_ADDR = 'ipc://{}'.format(os.path.join(RUNTIME_PATH, 'hunter.ipc'))
HUNTER_ADDR = os.environ.get('CIF_HUNTER_ADDR', HUNTER_ADDR)

HUNTER_SINK_ADDR = 'ipc://{}'.format(os.path.join(RUNTIME_PATH, 'hunter_sink.ipc'))
HUNTER_SINK_ADDR = os.environ.get('CIF_HUNTER_SINK_ADDR', HUNTER_SINK_ADDR)

GATHERER_ADDR = 'ipc://{}'.format(os.path.join(RUNTIME_PATH, 'gatherer.ipc'))
GATHERER_ADDR = os.environ.get('CIF_GATHERER_ADDR', GATHERER_ADDR)

GATHERER_SINK_ADDR = 'ipc://{}'.format(os.path.join(RUNTIME_PATH, 'gatherer_sink.ipc'))
GATHERER_SINK_ADDR = os.environ.get('CIF_GATHERER_SINK_ADDR', GATHERER_SINK_ADDR)

TOKEN_CACHE_DELAY = 5

HUNTER_RESOLVER_TIMEOUT = os.environ.get('CIF_HUNTER_RESOLVER_TIMEOUT', 5)

FEEDS_DAYS = 45
FEEDS_LIMIT = 50000
FEEDS_WHITELIST_LIMIT = 25000

HTTPD_FEED_WHITELIST_CONFIDENCE = os.getenv('CIF_HTTPD_FEED_WHITELIST_CONFIDENCE', 5)
