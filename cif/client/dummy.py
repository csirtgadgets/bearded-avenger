import logging
import requests
import time
import json

from pprint import pprint

from cif.client import Client


class Dummy(Client):

    def __init__(self, remote, token):
        super(Dummy, self).__init__(remote, token)

    def _get(self, uri, params={}):
        return []

    def _post(self, uri, data):
        return data

    def submit(self, **data):
        if isinstance(data, dict):
            data = self._kv_to_observable(data)

        return data

Plugin = Dummy