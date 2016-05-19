#!/usr/bin/env python

import inspect
import logging
import os
import pkgutil
import textwrap
import time
import ujson as json
from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter
import traceback
import yaml
from pprint import pprint
import arrow

import zmq
from zmq.eventloop import ioloop

import cif.store
from cif.constants import CTRL_ADDR, STORE_ADDR
from cifsdk.constants import REMOTE_ADDR, CONFIG_PATH
from cifsdk.exceptions import CIFConnectionError, AuthError
from cifsdk.utils import setup_logging, get_argument_parser, setup_signals

MOD_PATH = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))

STORE_PATH = os.path.join(MOD_PATH, "store")
RCVTIMEO = 5000
SNDTIMEO = 2000
LINGER = 3
STORE_DEFAULT = 'sqlite'
STORE_PLUGINS = ['cif.store.dummy', 'cif.store.sqlite', 'cif.store.elasticsearch', 'cif.store.rdflib']


class Store(object):
    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.stop()

    def __init__(self, store=STORE_DEFAULT, store_address=STORE_ADDR, loop=ioloop.IOLoop.instance(), *args, **kv):
        self.logger = logging.getLogger(__name__)
        self.context = zmq.Context()
        self.router = self.context.socket(zmq.ROUTER)
        self.store_addr = store_address
        self.connected = False
        self.ctrl = None
        self.loop = loop
        self.store = store

        # TODO replace with cif.utils.load_plugin
        self.logger.debug('store is: {}'.format(self.store))
        for loader, modname, is_pkg in pkgutil.iter_modules(cif.store.__path__, 'cif.store.'):
            self.logger.debug('testing store plugin: {}'.format(modname))
            if modname == 'cif.store.{}'.format(self.store) or modname == 'cif.store.z{}'.format(self.store):
                self.logger.debug('Loading plugin: {0}'.format(modname))
                self.store = loader.find_module(modname).load_module(modname)
                self.store = self.store.Plugin(*args, **kv)

        self.router = self.context.socket(zmq.ROUTER)

    def start(self):
        self.token_create_admin()
        while not self.connected:
            try:
                self.logger.debug('connecting to router: {0}'.format(self.router))
                self._connect_ctrl()
            except zmq.error.Again:
                self.logger.error("problem connecting to router, retrying...")
            except CIFConnectionError:
                self.logger.error("unable to connect")
                raise
            except KeyboardInterrupt:
                raise SystemExit
            else:
                self.connected = True

        self.router.connect(self.store_addr)

        self.logger.info('connected')
        self.loop.add_handler(self.router, self.handle_message, zmq.POLLIN)

        self.logger.debug('staring loop')
        self.loop.start()

    def stop(self):
        self.loop.stop()

    def _connect_ctrl(self):
        if self.ctrl:
            self.connected = False
            self.ctrl.close()
            self.ctrl = None

        self.ctrl = self.context.socket(zmq.REQ)
        self.ctrl.RCVTIMEO = RCVTIMEO
        self.ctrl.SNDTIMEO = SNDTIMEO
        self.ctrl.setsockopt(zmq.LINGER, LINGER)

        self.ctrl.connect(CTRL_ADDR)
        self.ctrl.send_multipart(['store', 'ping', str(time.time())])
        id, mtype, data = self.ctrl.recv_multipart()
        if mtype != 'ack':
            raise CIFConnectionError("connection rejected by router: {}".format(mtype))

    def handle_message(self, s, e):
        self.logger.debug('message received')
        m = s.recv_multipart()

        self.logger.debug(m)

        try:
            id, mtype, token, data = m
        except Exception as e:
            self.logger.error(e)
            self.logger.debug(m)
            traceback.print_exc()
            rv = {"status": "failed"}
            self.router.send_multipart([m[0], json.dumps(rv).encode('utf-8')])
            return

        if isinstance(data, basestring):
            try:
                data = json.loads(data)
            except ValueError as e:
                self.logger.error(e)
                self.router.send_multipart(["", json.dumps({"status": "failed"})])
                return

        handler = getattr(self, "handle_" + mtype)
        if handler:
            self.logger.debug("mtype: {0}".format(mtype))
            self.logger.debug('running handler: {}'.format(mtype))

            try:
                rv = handler(token, data)
                rv = {"status": "success", "data": rv}
                self.store.token_last_activity_at(token, timestamp=arrow.utcnow())
            except AuthError as e:
                self.logger.error(e)
                rv = {'status': 'failed', 'message': 'unauthorized'}
            except Exception as e:
                self.logger.error(e)
                traceback.print_exc()
                rv = {"status": "failed"}

            self.router.send_multipart([id, json.dumps(rv).encode('utf-8')])
        else:
            self.logger.error('message type {0} unknown'.format(mtype))
            self.router.send_multipart([id, '0'])

    def handle_ping(self, token, data='[]'):
        self.logger.debug('handling ping message')
        return self.store.ping(token)

    def handle_ping_write(self, token, data='[]'):
        self.logger.debug('handling ping write')
        return self.store.token_write(token)

    def handle_indicators_search(self, token, data):
        if self.store.token_read(token):
            self.logger.debug('searching')
            return self.store.indicators_search(token, data)
        else:
            raise AuthError('invalid token')

    # TODO group check
    def handle_indicators_create(self, token, data):
        if self.store.token_write(token):
            return self.store.indicators_create(token, data)
        else:
            raise AuthError('invalid token')

    def handle_tokens_search(self, token, data):
        if self.store.token_admin(token):
            self.logger.debug('tokens_search')
            return self.store.tokens_search(data)
        else:
            raise AuthError('invalid token')

    def handle_tokens_create(self, token, data):
        if self.store.token_admin(token):
            self.logger.debug('tokens_create')
            return self.store.tokens_create(data)
        else:
            raise AuthError('invalid token')

    def handle_tokens_delete(self, token, data):
        if self.store.token_admin(token):
            return self.store.tokens_delete(data)
        else:
            raise AuthError('invalid token')

    def handle_token_write(self, token, data=None):
        return self.store.token_write(token)

    def handle_tokens_edit(self, token, data):
        if self.store.token_admin(token):
            return self.store.token_edit(data)
        else:
            raise AuthError('invalid token')

    def token_create_admin(self):
        self.logger.info('testing for tokens...')
        if not self.store.tokens_admin_exists():
            self.logger.info('admin token does not exist, generating..')
            rv = self.store.tokens_create({
                'username': u'admin',
                'groups': [u'everyone'],
                'read': u'1',
                'write': u'1',
                'admin': u'1'
            })
            self.logger.info('admin token created: {}'.format(rv['token']))
            return rv['token']
        else:
            self.logger.info('admin token exists...')

    def token_create_smrt(self):
        self.logger.info('generating smrt token')
        rv = self.store.tokens_create({
            'username': u'csirtg-smrt',
            'groups': [u'everyone'],
            'write': u'1',
        })
        self.logger.info('admin token created: {}'.format(rv['token']))
        return rv['token']

    def token_create_hunter(self):
        self.logger.info('generating hunter token')
        rv = self.store.tokens_create({
            'username': u'hunter',
            'groups': [u'everyone'],
            'write': u'1',
        })
        self.logger.info('admin token created: {}'.format(rv['token']))
        return rv['token']


def main():
    p = get_argument_parser()
    p = ArgumentParser(
        description=textwrap.dedent('''\
         Env Variables:
            CIF_RUNTIME_PATH
            CIF_STORE_ADDR

        example usage:
            $ cif-store -d
        '''),
        formatter_class=RawDescriptionHelpFormatter,
        prog='cif-store',
        parents=[p]
    )

    p.add_argument("--store-address", help="specify the store address cif-router is listening on[default: %("
                                             "default)s]", default=STORE_ADDR)

    p.add_argument("--store", help="specify a store type {} [default: %(default)s]".format(', '.join(STORE_PLUGINS)),
                   default=STORE_DEFAULT)

    p.add_argument('--config', help='specify config path [default %(default)s]', default=CONFIG_PATH)

    p.add_argument('--token-create-admin', help='generate an admin token')
    p.add_argument('--token-create-smrt')
    p.add_argument('--token-create-smrt-remote', default=REMOTE_ADDR)
    p.add_argument('--token-create-hunter')

    args = p.parse_args()

    pprint(args)

    setup_logging(args)
    logger = logging.getLogger(__name__)
    logger.info('loglevel is: {}'.format(logging.getLevelName(logger.getEffectiveLevel())))

    setup_signals(__name__)

    # from cif.reloader import ModuleWatcher
    # mw = ModuleWatcher()
    # mw.watch_module('cif.store')
    # mw.start_watching()

    start = True
    if args.token_create_smrt:
        start = False
        with Store(store=args.store) as s:
            t = s.token_create_smrt()
            if t:
                data = {
                    'token': str(t),
                }
                with open(args.token_create_smrt, 'w') as f:
                    f.write(yaml.dump(data, default_flow_style=False))

                logger.info('token config generated: {}'.format(args.token_create_smrt))
            else:
                logger.error('token not created')

    if args.token_create_hunter:
        start = False
        with Store(store=args.store) as s:
            t = s.token_create_hunter()
            if t:
                data = {
                    'token': str(t),
                }
                with open(args.token_create_hunter, 'w') as f:
                    f.write(yaml.dump(data, default_flow_style=False))

                logger.info('token config generated: {}'.format(args.token_create_hunter))
            else:
                logger.error('token not created')

    if args.token_create_admin:
        start = False
        with Store(store=args.store) as s:
            t = s.token_create_admin()
            if t:
                data = {
                    'token': str(t),
                }
                with open(args.token_create_admin, 'w') as f:
                    f.write(yaml.dump(data, default_flow_style=False))

                logger.info('token config generated: {}'.format(args.token_create_admin))
            else:
                logger.error('token not created')

    if start:
        with Store(store_address=args.store_address, store=args.store) as s:
            try:
                logger.info('starting up...')
                s.start()
            except KeyboardInterrupt:
                logger.info('shutting down...')



    # mw.stop_watching()

if __name__ == "__main__":
    main()
