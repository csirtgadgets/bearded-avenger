from sqlalchemy.types import UserDefinedType
from sqlalchemy.ext.declarative import declarative_base
from binascii import hexlify, unhexlify
import socket

Base = declarative_base()


class Ip(UserDefinedType):
    # http://docs.sqlalchemy.org/en/latest/_modules/examples/postgis/postgis.html
    # http://docs.sqlalchemy.org/en/latest/core/custom_types.html#creating-new-types
    def __init__(self, version=4):
        self.version = version

    def get_col_spec(self, **kw):
        return "IP"

    def bind_processor(self, dialect):
        def process(value):
            if self.version == 6:
                return socket.inet_pton(socket.AF_INET6, value)
            return socket.inet_pton(socket.AF_INET, value)

        return process

    def result_processor(self, dialect, coltype):
        def process(value):
            return socket.inet_ntoa(value)

        return process