from sqlalchemy.types import UserDefinedType
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import types
from cifsdk.constants import PYVERSION
from pprint import pprint
import binascii
import socket

Base = declarative_base()


class Ip(UserDefinedType):
    # http://docs.sqlalchemy.org/en/latest/_modules/examples/postgis/postgis.html
    # http://docs.sqlalchemy.org/en/latest/core/custom_types.html#creating-new-types
    # http://sqlalchemy-utils.readthedocs.io/en/latest/_modules/sqlalchemy_utils/types/uuid.html

    impl = types.BINARY(16)

    def __init__(self, version=4):
        self.version = version

    def get_col_spec(self, **kw):
        return "IP"

    def bind_processor(self, dialect):

        DBAPIBinary = dialect.dbapi.Binary

        def process(value):
            if self.version == 6:
                value = socket.inet_pton(socket.AF_INET6, value)
            else:
                value = socket.inet_pton(socket.AF_INET, value)

            return DBAPIBinary(value)

        return process

    def result_processor(self, dialect, coltype):
        def process(value):
            value = socket.inet_ntop(value)
            return value

        return process

    @property
    def python_type(self):
        return self.impl.type.python_type