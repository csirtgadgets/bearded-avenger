from sqlalchemy.types import UserDefinedType
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import types

Base = declarative_base()


class Hash(UserDefinedType):

    impl = types.BINARY(16)

    def __init__(self, version=4):
        self.version = version

    def get_col_spec(self, **kw):
        return 'HASH'

    def bind_processor(self, dialect):

        DBAPIBinary = dialect.dbapi.Binary

        def process(value):
            if type(value) == str:
                value = value.encode('utf-8')
            return DBAPIBinary(value)

        return process

    def result_processor(self, dialect, coltype):
        def process(value):
            return value

        return process

    @property
    def python_type(self):
        return self.impl.type.python_type
