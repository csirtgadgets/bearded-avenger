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

    @abc.abstractmethod
    def admin_exists(self):
        raise NotImplementedError

    @abc.abstractmethod
    def create(self, data):
        raise NotImplementedError

    @abc.abstractmethod
    def delete(self, data):
        raise NotImplementedError

    @abc.abstractmethod
    def search(self, data):
        raise NotImplementedError

    @abc.abstractmethod
    def admin(self, token):
        raise NotImplementedError

    @abc.abstractmethod
    def read(self, token):
        raise NotImplementedError

    @abc.abstractmethod
    def write(self, token):
        raise NotImplementedError

    @abc.abstractmethod
    def edit(self, data):
        raise NotImplementedError

    @abc.abstractmethod
    def indicators_search(self, token, data):
        raise NotImplementedError

    @abc.abstractmethod
    def indicators_create(self, token, data):
        raise NotImplementedError

    @abc.abstractmethod
    def indicators_upsert(self, token, data):
        raise NotImplementedError
