import os.path
import tempfile

from ._version import get_versions
VERSION = get_versions()['version']
del get_versions

TEMP_DIR = os.path.join(tempfile.gettempdir())
RUNTIME_PATH = os.environ.get('CIF_RUNTIME_PATH', TEMP_DIR)
RUNTIME_PATH = os.path.join(RUNTIME_PATH)

# Logging stuff
LOG_FORMAT = '%(asctime)s - %(levelname)s - %(name)s[%(lineno)s] - %(message)s'

LOGLEVEL = 'INFO'
LOGLEVEL = os.environ.get('CIF_LOGLEVEL', LOGLEVEL).upper()

CONFIG_PATH = os.environ.get('CIF_CONFIG',
                             os.environ.get('CIF_CONFIG', os.path.join(os.path.expanduser('~/'), '.cif.yml')))

# address stuff

REMOTE_ADDR = 'http://localhost:5000'
REMOTE_ADDR = os.environ.get('CIF_REMOTE_ADDR', REMOTE_ADDR)

ROUTER_ADDR = "ipc://{}".format(os.path.join(RUNTIME_PATH, 'router.ipc'))
ROUTER_ADDR = os.environ.get('CIF_ROUTER_ADDR', ROUTER_ADDR)

STORAGE_ADDR = 'ipc://{}'.format(os.path.join(RUNTIME_PATH, 'storage.ipc'))
STORAGE_ADDR = os.environ.get('CIF_STORAGE_ADDR', STORAGE_ADDR)

CTRL_ADDR = 'ipc://{}'.format(os.path.join(RUNTIME_PATH, 'ctrl.ipc'))
CTRL_ADDR = os.environ.get('CIF_CTRL_ADDR', CTRL_ADDR)

GATHER_ADDR = 'ipc://{}'.format(os.path.join(RUNTIME_PATH, 'gather.ipc'))
GATHER_ADDR = os.environ.get('CIF_GATHER_ADDR', GATHER_ADDR)

HUNTER_ADDR = 'ipc://{}'.format(os.path.join(RUNTIME_PATH, 'hunter.ipc'))
HUNTER_ADDR = os.environ.get('CIF_HUNTER_ADDR', HUNTER_ADDR)

SMRT_CACHE = os.path.join(RUNTIME_PATH, 'smrt')
SMRT_CACHE = os.environ.get('CIF_SMRT_CACHE', SMRT_CACHE)

SMRT_RULES_PATH = os.path.join(RUNTIME_PATH, 'smrt', 'rules')
SMRT_RULES_PATH = os.environ.get('CIF_SMRT_RULES_PATH', SMRT_RULES_PATH)

SEARCH_LIMIT = os.environ.get('CIF_SEARCH_LIMIT', 500)
SEARCH_CONFIDENCE = os.environ.get('CIF_SEARCH_CONFIDENCE', 50)