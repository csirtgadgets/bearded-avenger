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

    def _token_generate(self):
        return binascii.b2a_hex(os.urandom(TOKEN_LENGTH))

    @abc.abstractmethod
    def tokens_admin_exists(self):
        raise NotImplementedError

    @abc.abstractmethod
    def tokens_create(self, data):
        raise NotImplementedError

    @abc.abstractmethod
    def tokens_delete(self, data):
        raise NotImplementedError

    @abc.abstractmethod
    def tokens_search(self, data):
        raise NotImplementedError

    @abc.abstractmethod
    def token_admin(self, token):
        raise NotImplementedError

    @abc.abstractmethod
    def token_read(self, token):
        raise NotImplementedError

    @abc.abstractmethod
    def token_write(self, token):
        raise NotImplementedError

    @abc.abstractmethod
    def token_edit(self, data):
        raise NotImplementedError

    @abc.abstractmethod
    def token_last_activity_at(self, token, timestamp=None):
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
