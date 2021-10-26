import abc


class Auth(object):
    __metaclass__ = abc.ABCMeta

    name = 'base'

    @abc.abstractmethod
    def __init__(self, **kwargs):
        raise NotImplementedError
