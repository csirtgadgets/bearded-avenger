#!/usr/bin/env python

import ujson as json
import logging
import zmq
import multiprocessing
import cif.auth
from cifsdk.msg import Msg
from cifsdk.exceptions import AuthError
import os
import time
import pkgutil
import arrow

from cif.constants import AUTH_ADDR
from cif.utils import strtobool

SNDTIMEO = 2000

AUTH_PROVIDER = os.environ.get('CIF_AUTH_PROVIDER', 'cif_store')
AUTH_ERR = json.dumps({'status': 'failed', 'message': 'unauthorized'})

logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)

TRACE = strtobool(os.environ.get('CIF_AUTH_TRACE', True))
if TRACE:
    logger.setLevel(logging.DEBUG)


class Auth(multiprocessing.Process):
    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        return self

    def __init__(self, auth_address=AUTH_ADDR, auth_type=AUTH_PROVIDER, **kwargs):
        multiprocessing.Process.__init__(self)
        self.auth_address = auth_address
        self.auth_type = auth_type
        self.kwargs = kwargs
        self.exit = multiprocessing.Event()

    def _load_plugin(self, **kwargs):
        logger.debug('loading auth provider {}...'.format(AUTH_PROVIDER))
        for loader, modname, is_pkg in pkgutil.iter_modules(cif.auth.__path__, 'cif.auth.'):
            if modname == 'cif.auth.{}'.format(self.auth_type):
                self.auth = loader.find_module(modname).load_module(modname)
                self.auth = self.auth.Plugin(**kwargs)
                logger.debug('plugin loaded: {}'.format(modname))

    def terminate(self):
        self.exit.set()

    def start(self):
        self._load_plugin(**self.kwargs)

        context = zmq.Context()
        auth_s = context.socket(zmq.ROUTER)

        auth_s.SNDTIMEO = SNDTIMEO

        logger.debug('connecting to sockets...')
        auth_s.connect(self.auth_address)
        logger.debug('connected. starting loop')

        poller = zmq.Poller()
        poller.register(auth_s, zmq.POLLIN)

        while not self.exit.is_set():
            try:
                s = dict(poller.poll(1000))
            except SystemExit or KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(e)
                break

            if auth_s in s:
                id, client_id, token, mtype, data = Msg().recv(auth_s)

                start = time.time()

                try:
                    token = self.auth.handle_token_search(token)
                    token = self.check_token_perms(mtype, token, data)

                except AuthError as e:
                    logger.error(e)
                    token = []
                    data = AUTH_ERR

                except ValueError as e:
                    logger.error(e)
                    token = []
                    data = AUTH_ERR

                token = json.dumps(token)
                logger.debug('sending auth info back to cif-router: %f' % (time.time() - start))
                Msg(id=id, client_id=client_id, token=token, mtype=mtype, data=data).send(auth_s)

        logger.info('shutting down auth...')

    def check_token_perms(self, mtype, token, data):
        """Check token perms/groups and raise AuthError if issues
        :param mtype(str)
        :param token(list) - from self.auth.handle_token_search
        :param data(str) - a str dumped dict from Msg()
        :return token(dict) - matched token dict
        """
        if not token:
            raise AuthError('Auth: invalid token provided to API')
        # if more than one token comes back, shenanigans
        elif len(token) > 1:
            raise AuthError('multiple token matches during auth. possible wildcard attempt?')
        
        token = token[0]

        if token.get('revoked') or (token.get('expires') and token['expires'] < arrow.utcnow().datetime.strftime('%Y-%m-%dT%H:%M:%S.%fZ')):
            raise AuthError('Auth: token revoked ({}) or expired ({})'.format(token.get('revoked'), token.get('expires')))
        else:
            # check action (mtype) against token perms
            if mtype.startswith('tokens') or mtype.endswith('delete'):
                if not token.get('admin'):
                    raise AuthError('Auth: admin function attempted but supplied token had no admin permission')
            elif mtype.endswith('create') or mtype.endswith('write'):
                if not token.get('write'):
                    raise AuthError('Auth: write function attempted but supplied token had no write permission')
            elif mtype == 'indicators_search':
                if not token.get('read'):
                    raise AuthError('Auth: read function attempt but supplied token had no read permission')

            # check action (mtype) against token groups
            if mtype == 'indicators_create':
                data = json.loads(data)
                if isinstance(data, dict):
                    data = [data]
                for i in data:
                    if i.get('group', 'everyone') not in token['groups']:
                        raise AuthError('Auth: indicator function attempt {} but supplied indicator group {} did not match user token groups {}'.format(mtype, i.get('group', 'everyone'), token['groups']))
                # for indicators_search and _delete, they use plural "groups"

            return token
