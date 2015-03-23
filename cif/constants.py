

LOG_FORMAT = '%(asctime)s - %(levelname)s - %(name)s::%(threadName)s - %(message)s'
REMOTE = 'http://localhost:5000'

ROUTER_FRONTEND = 'ipc://frontend.ipc'
ROUTER_GATHERER = 'ipc://gatherer.ipc'
ROUTER_PUBLISHER = 'ipc://publisher.ipc'
STORAGE_ADDR = 'ipc://storage.ipc'
CTRL_ADDR = 'ipc://ctrl.ipc'

DEFAULT_CONFIG = ".cifv3.yml"

VERSION = '3.0.0a1'