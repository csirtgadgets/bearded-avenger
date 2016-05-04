import logging
import requests
import time
import json
from cif.exceptions import AuthError
from pprint import pprint

from cif.client import Client


class HTTP(Client):

    def __init__(self, remote, token, proxy=None, timeout=300, verify_ssl=True, **kwargs):
        super(HTTP, self).__init__(remote, token, *kwargs)

        self.proxy = proxy
        self.timeout = timeout
        self.verify_ssl = verify_ssl

        self.session = requests.Session()
        self.session.headers["Accept"] = 'application/vnd.cif.v3+json'
        self.session.headers['User-Agent'] = 'cif-sdk-python/0.0.0a'
        self.session.headers['Authorization'] = 'Token token=' + self.token
        self.session.headers['Content-Type'] = 'application/json'

    def _get(self, uri, params={}):
        uri = self.remote + uri
        body = self.session.get(uri, params=params, verify=self.verify_ssl)

        if body.status_code > 303:
            err = 'request failed: %s' % str(body.status_code)
            self.logger.debug(err)

            if body.status_code == 401:
                raise AuthError('invalid token')
            elif body.status_code == 404:
                err = 'not found'
                raise RuntimeError(err)
            else:
                try:
                    err = json.loads(body.content).get('message')
                except ValueError as e:
                    err = body.content
                    self.logger.error(err)
                    raise RuntimeError(err)

        return json.loads(body.content)

    def _post(self, uri, data):
        body = self.session.post(uri, data=json.dumps(data))

        if body.status_code > 303:
            err = 'request failed: %s' % str(body.status_code)
            self.logger.debug(err)
            err = body.content

            if body.status_code == 401:
                raise AuthError('invalid token')
            elif body.status_code == 404:
                err = 'not found'
                raise RuntimeError(err)
            else:
                try:
                    err = json.loads(err).get('message')
                except ValueError as e:
                    err = body.content

                self.logger.error(err)
                raise RuntimeError(err)

        self.logger.debug(body.content)
        body = json.loads(body.content)
        return body

    def _delete(self, uri, data):
        body = self.session.delete(uri, data=json.dumps(data))

        if body.status_code > 303:
            err = 'request failed: %s' % str(body.status_code)
            self.logger.debug(err)
            err = body.content

            if body.status_code == 401:
                raise AuthError('invalid token')
            elif body.status_code == 404:
                err = 'not found'
                raise RuntimeError(err)
            else:
                try:
                    err = json.loads(err).get('message')
                except ValueError as e:
                    err = body.content

                self.logger.error(err)
                raise RuntimeError(err)

        self.logger.debug(body.content)
        body = json.loads(body.content)
        return body

    def search(self, filters):
        rv = self._get('/search', params=filters)
        return rv['data']

    def submit(self, data):
        data = str(data)

        uri = "{0}/indicators".format(self.remote)
        self.logger.debug(uri)
        rv = self._post(uri, data)
        return rv["data"]

    def ping(self):
        t0 = time.time()

        self._get('/ping')

        t1 = (time.time() - t0)
        self.logger.debug('return time: %.15f' % t1)
        return t1

    def tokens_search(self, filters):
        rv = self._get('{}/tokens'.format(self.remote), params=filters)
        return rv['data']

    def tokens_delete(self, token):
        rv = self._delete('{}/tokens'.format(self.remote), {'token': token})
        return rv['data']

    def tokens_create(self, data):
        self.logger.debug(data)
        rv = self._post('{}/tokens'.format(self.remote), data)
        return rv['data']

Plugin = HTTP
