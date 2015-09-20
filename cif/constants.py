import os.path
import tempfile

TEMP_DIR = os.path.join(tempfile.gettempdir(), 'cif')

LOG_FORMAT = '%(asctime)s - %(levelname)s - %(name)s[%(lineno)s] - %(message)s'
REMOTE = 'http://localhost:5000'

ROUTER_FRONTEND = "ipc://{}".format(os.path.join(TEMP_DIR, 'frontend.ipc')
ROUTER_GATHERER = 'ipc://{}'.format(os.path.join(TEMP_DIR, 'gatherer.ipc'))
ROUTER_PUBLISHER = 'ipc://{}'.format(os.path.join(TEMP_DIR, 'publisher.ipc'))
STORAGE_ADDR = 'ipc://{}'.format(os.path.join(TEMP_DIR, 'storage.ipc'))
CTRL_ADDR = 'ipc://{}'.format(os.path.join(TEMP_DIR, 'ctrl.ipc')

DEFAULT_CONFIG = ".cif.yml"

VERSION = '3.0.0a1'

RUNTIME_PATH = os.path.join(os.path.expanduser("~"), ".cif")
