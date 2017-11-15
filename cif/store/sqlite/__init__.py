import logging
import os

from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.engine import Engine
import sqlite3

from cifsdk.constants import RUNTIME_PATH
from cif.store.plugin import Store
from cifsdk.constants import PYVERSION

Base = declarative_base()
from .token import TokenManager, Token
from .indicator import Indicator, IndicatorManager

DATA_PATH = os.getenv('CIF_DATA_PATH')
DB_FILE = os.path.join(RUNTIME_PATH, 'cif.sqlite')

if DATA_PATH:
    DB_FILE = os.path.join(DATA_PATH, 'cif.db')

logger = logging.getLogger(__name__)
TRACE = os.environ.get('CIF_STORE_SQLITE_TRACE')

# http://stackoverflow.com/q/9671490/7205341
SYNC = os.environ.get('CIF_STORE_SQLITE_SYNC', 'NORMAL')

# https://www.sqlite.org/pragma.html#pragma_cache_size
CACHE_SIZE = os.environ.get('CIF_STORE_SQLITE_CACHE_SIZE', 512000000)  # 256MB

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

if not TRACE:
    logger.setLevel(logging.ERROR)
    logging.getLogger('sqlalchemy.engine').setLevel(logging.ERROR)

VALID_FILTERS = ['indicator', 'confidence', 'provider', 'itype', 'group', 'tags']

if PYVERSION > 2:
    basestring = (str, bytes)


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode = MEMORY")
    cursor.execute("PRAGMA synchronous = {}".format(SYNC))
    cursor.execute("PRAGMA temp_store = MEMORY")
    cursor.execute("PRAGMA cache_size = {}".format(CACHE_SIZE))
    cursor.close()


class SQLite(Store):
    # http://www.pythoncentral.io/sqlalchemy-orm-examples/
    name = 'sqlite'

    def __init__(self, dbfile=DB_FILE, autocommit=False, dictrows=True, **kwargs):
        self.logger = logging.getLogger(__name__)

        self.dbfile = dbfile
        self.autocommit = autocommit
        self.dictrows = dictrows
        self.path = "sqlite:///{0}".format(self.dbfile)

        echo = False
        if TRACE:
            echo = False

        # http://docs.sqlalchemy.org/en/latest/orm/contextual.html
        self.engine = create_engine(self.path, echo=echo)
        self.handle = sessionmaker(bind=self.engine)
        self.handle = scoped_session(self.handle)

        Base.metadata.create_all(self.engine)

        self.logger.debug('database path: {}'.format(self.path))

        self.tokens = TokenManager(self.handle, self.engine)
        self.indicators = IndicatorManager(self.handle, self.engine)

    def ping(self, token):
        if self.tokens.read(token) or self.tokens.write(token):
            return True

Plugin = SQLite
