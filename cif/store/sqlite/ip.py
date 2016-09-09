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

    impl = types.Unicode(255)

    def __init__(self, max_length=255, version=4):
        self.version = version
        self.impl = types.Unicode(max_length)

    def get_col_spec(self, **kw):
        return "IP"

    def bind_processor(self, dialect):
        def process(value):
            if self.version == 6:
                value = socket.inet_pton(socket.AF_INET6, value)
            else:
                value = socket.inet_pton(socket.AF_INET, value)

            if PYVERSION < 3:
                value = binascii.b2a_uu(value)
            return value

        return process

    def result_processor(self, dialect, coltype):
        def process(value):
            return socket.inet_ntoa(binascii.a2b_uu(value))

        return process

    @property
    def python_type(self):
        return self.impl.type.python_type