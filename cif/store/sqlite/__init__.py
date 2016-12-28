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
from cif.constants import TOKEN_CACHE_DELAY
import arrow

Base = declarative_base()
from .token import TokenMixin, Token
from .indicator import Indicator, IndicatorMixin

DB_FILE = os.path.join(RUNTIME_PATH, 'cif.sqlite')

logger = logging.getLogger(__name__)
TRACE = os.environ.get('CIF_STORE_SQLITE_TRACE')

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

if not TRACE:
    logger.setLevel(logging.ERROR)

VALID_FILTERS = ['indicator', 'confidence', 'provider', 'itype', 'group', 'tags']

if PYVERSION > 2:
    basestring = (str, bytes)


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


class SQLite(IndicatorMixin, TokenMixin, Store):
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
            echo = True

        # http://docs.sqlalchemy.org/en/latest/orm/contextual.html
        self.engine = create_engine(self.path, echo=echo)
        self.handle = sessionmaker(bind=self.engine)
        self.handle = scoped_session(self.handle)

        Base.metadata.create_all(self.engine)

        self.logger.debug('database path: {}'.format(self.path))

        self.token_cache = {}
        self.token_cache_check = arrow.utcnow().timestamp + TOKEN_CACHE_DELAY


    def ping(self, token):
        if self.token_read(token) or self.token_write(token):
            return True

Plugin = SQLite
