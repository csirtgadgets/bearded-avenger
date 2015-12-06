import os.path
import tempfile

VERSION = '3.0.0a1'

RUNTIME_PATH = os.path.join(os.path.expanduser("~"), ".cif")


# Logging stuff
LOG_FORMAT = '%(asctime)s - %(levelname)s - %(name)s[%(lineno)s] - %(message)s'

LOGLEVEL = 'INFO'
LOGLEVEL = os.environ.get('CIF_LOGLEVEL', LOGLEVEL).upper()

# address stuff
TEMP_DIR = os.path.join(tempfile.gettempdir())
REMOTE_ADDR = 'http://localhost:5000'
REMOTE_ADDR = os.environ.get('CIF_REMOTE_ADDR', REMOTE_ADDR)

ROUTER_ADDR = "ipc://{}".format(os.path.join(TEMP_DIR, 'router.ipc'))
ROUTER_ADDR = os.environ.get('CIF_ROUTER_ADDR', ROUTER_ADDR)

STORAGE_ADDR = 'ipc://{}'.format(os.path.join(TEMP_DIR, 'storage.ipc'))
STORAGE_ADDR = os.environ.get('CIF_STORAGE_ADDR', STORAGE_ADDR)

CTRL_ADDR = 'ipc://{}'.format(os.path.join(TEMP_DIR, 'ctrl.ipc'))
CTRL_ADDR = os.environ.get('CIF_CTRL_ADDR', CTRL_ADDR)

GATHER_ADDR = 'ipc://{}'.format(os.path.join(TEMP_DIR, 'gather.ipc'))
GATHER_ADDR = os.environ.get('CIF_GATHER_ADDR', GATHER_ADDR)

HUNTER_ADDR = 'ipc://{}'.format(os.path.join(TEMP_DIR, 'hunter.ipc'))
HUNTER_ADDR = os.environ.get('CIF_HUNTER_ADDR', HUNTER_ADDR)

SMRT_CACHE = os.path.join('var', 'smrt')
SMRT_CACHE = os.environ.get('CIF_SMRT_CACHE', SMRT_CACHE)
