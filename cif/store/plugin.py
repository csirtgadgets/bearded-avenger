import abc
import os
import binascii

from cif.constants import TOKEN_LENGTH


class Store(object):
    __metaclass__ = abc.ABCMeta

    name = 'base'

    @abc.abstractmethod
    def __init__(self):
        raise NotImplementedError

    @abc.abstractmethod
    def ping(self, token):
        return True

