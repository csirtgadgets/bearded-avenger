#!/usr/bin/env python

import inspect
import logging
import os
import pkgutil
import textwrap
import ujson as json
from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter
import traceback
import yaml
from pprint import pprint
import arrow
import multiprocessing

import zmq

import cif.store
from cif.constants import STORE_ADDR, PYVERSION
from cifsdk.constants import REMOTE_ADDR, CONFIG_PATH
from cifsdk.exceptions import AuthError, InvalidSearch
from csirtg_indicator import InvalidIndicator
from cifsdk.utils import setup_logging, get_argument_parser, setup_signals

MOD_PATH = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))

STORE_PATH = os.path.join(MOD_PATH, "store")
RCVTIMEO = 5000
SNDTIMEO = 2000
LINGER = 3
STORE_DEFAULT = 'sqlite'
STORE_PLUGINS = ['cif.store.dummy', 'cif.store.sqlite', 'cif.store.elasticsearch', 'cif.store.rdflib']
if PYVERSION > 2:
    basestring = (str, bytes)
    
logger = logging.getLogger(__name__)


class Store(multiprocessing.Process):
    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        return self

    def __init__(self, store_type=STORE_DEFAULT, store_address=STORE_ADDR, **kwargs):
        multiprocessing.Process.__init__(self)
        self.store_addr = store_address
        self.store = store_type
        self.kwargs = kwargs
        self.exit = multiprocessing.Event()

    def _load_plugin(self, **kwargs):
        # TODO replace with cif.utils.load_plugin
        logger.debug('store is: {}'.format(self.store))
        for loader, modname, is_pkg in pkgutil.iter_modules(cif.store.__path__, 'cif.store.'):
            logger.debug('testing store plugin: {}'.format(modname))
            if modname == 'cif.store.{}'.format(self.store) or modname == 'cif.store.z{}'.format(self.store):
                logger.debug('Loading plugin: {0}'.format(modname))
                self.store = loader.find_module(modname).load_module(modname)
                self.store = self.store.Plugin(**kwargs)

    def start(self):
        self._load_plugin(**self.kwargs)
        self.context = zmq.Context()
        self.router = self.context.socket(zmq.ROUTER)

        self.token_create_admin()

        logger.debug('connecting to router: {}'.format(self.store_addr))
        self.router.connect(self.store_addr)

        logger.info('connected')

        logger.debug('staring loop')

        poller = zmq.Poller()
        poller.register(self.router, zmq.POLLIN)

        while not self.exit.is_set():
            try:
                m = dict(poller.poll(1000))
            except SystemExit or KeyboardInterrupt:
                break

            if self.router in m:
                m = self.router.recv_multipart()
                self.handle_message(m)

    def terminate(self):
        self.exit.set()

    def handle_message(self, m):
        logger.debug('message received')

        id, client_id, null, mtype, token, data = m

        if isinstance(data, basestring):

            try:
                data = json.loads(data.decode('utf-8'))
            except ValueError as e:
                logger.error(e)
                self.router.send_multipart([id, client_id, null, mtype, json.dumps({"status": "failed"}).encode('utf-8')])
                return

        handler = getattr(self, "handle_" + mtype.decode('utf-8'))
        if handler:
            logger.debug("mtype: {0}".format(mtype))
            logger.debug('running handler: {}'.format(mtype))

            try:
                rv = handler(token.decode('utf-8'), data)
                rv = {"status": "success", "data": rv}
                logger.debug('updating last_active')
                ts = arrow.utcnow().format('YYYY-MM-DDTHH:mm:ss.SSSSS')
                ts = '{}Z'.format(ts)
                self.store.token_last_activity_at(token, timestamp=ts)
            except AuthError as e:
                logger.error(e)
                rv = {'status': 'failed', 'message': 'unauthorized'}
            except InvalidSearch as e:
                rv = {'status': 'failed', 'message': 'invalid search'}
            except InvalidIndicator as e:
                logger.error(data)
                logger.error(e)
                traceback.print_exc()
                rv = {'status': 'failed', 'message': 'invalid indicator {}'.format(e)}
            except Exception as e:
                logger.error(e)
                traceback.print_exc()
                rv = {"status": "failed"}

            self.router.send_multipart([id, client_id, null, mtype, json.dumps(rv).encode('utf-8')])
        else:
            logger.error('message type {0} unknown'.format(mtype))
            self.router.send_multipart([id, null, '0'.encode('utf-8')])

    def handle_ping(self, token, data='[]'):
        logger.debug('handling ping message')
        return self.store.ping(token)

    def handle_ping_write(self, token, data='[]'):
        logger.debug('handling ping write')
        return self.store.token_write(token)

    def handle_indicators_search(self, token, data):
        if self.store.token_read(token):
            logger.debug('searching')
            try:
                x = self.store.indicators_search(data)
            except Exception as e:
                logger.error(e)
                raise InvalidSearch('invalid search')
            else:
                return x
        else:
            raise AuthError('invalid token')

    # TODO group check
    def handle_indicators_create(self, token, data):
        if self.store.token_write(token):
            return self.store.indicators_upsert(data)
        else:
            raise AuthError('invalid token')

    def handle_tokens_search(self, token, data):
        if self.store.token_admin(token):
            logger.debug('tokens_search')
            return self.store.tokens_search(data)
        else:
            raise AuthError('invalid token')

    def handle_tokens_create(self, token, data):
        if self.store.token_admin(token):
            logger.debug('tokens_create')
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
        logger.info('testing for tokens...')
        if not self.store.tokens_admin_exists():
            logger.info('admin token does not exist, generating..')
            rv = self.store.tokens_create({
                'username': u'admin',
                'groups': [u'everyone'],
                'read': u'1',
                'write': u'1',
                'admin': u'1'
            })
            logger.info('admin token created: {}'.format(rv['token']))
            return rv['token']
        else:
            logger.info('admin token exists...')

    def token_create_smrt(self):
        logger.info('generating smrt token')
        rv = self.store.tokens_create({
            'username': u'csirtg-smrt',
            'groups': [u'everyone'],
            'write': u'1',
        })
        logger.info('smrt token created: {}'.format(rv['token']))
        return rv['token']

    def token_create_hunter(self):
        logger.info('generating hunter token')
        rv = self.store.tokens_create({
            'username': u'hunter',
            'groups': [u'everyone'],
            'write': u'1',
        })
        logger.info('hunter token created: {}'.format(rv['token']))
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

    p.add_argument('--store-type')
    p.add_argument('--nodes')

    p.add_argument('--config', help='specify config path [default %(default)s]', default=CONFIG_PATH)

    p.add_argument('--token-create-admin', help='generate an admin token')
    p.add_argument('--token-create-smrt')
    p.add_argument('--token-create-smrt-remote', default=REMOTE_ADDR)
    p.add_argument('--token-create-hunter')

    p.add_argument('--remote', help='specify remote')

    args = p.parse_args()

    setup_logging(args)
    logger = logging.getLogger(__name__)
    logger.info('loglevel is: {}'.format(logging.getLevelName(logger.getEffectiveLevel())))

    setup_signals(__name__)

    if args.token_create_smrt:
        with Store(store_type=args.store, nodes=args.nodes) as s:
            s._load_plugin(store_type=args.store, nodes=args.nodes)
            t = s.token_create_smrt()
            if t:
                data = {
                    'token': t.encode('utf-8'),
                }
                if args.remote:
                    data['remote'] = args.remote

                with open(args.token_create_smrt, 'w') as f:
                    f.write(yaml.dump(data, default_flow_style=False))

                logger.info('token config generated: {}'.format(args.token_create_smrt))
            else:
                logger.error('token not created')

    if args.token_create_hunter:
        with Store(store_type=args.store, nodes=args.nodes) as s:
            s._load_plugin(store_type=args.store, nodes=args.nodes)
            t = s.token_create_hunter()
            if t:
                data = {
                    'hunter_token': t.encode('utf-8'),
                }
                with open(args.token_create_hunter, 'w') as f:
                    f.write(yaml.dump(data, default_flow_style=False))

                logger.info('token config generated: {}'.format(args.token_create_hunter))
            else:
                logger.error('token not created')

    if args.token_create_admin:
        with Store(store_type=args.store, nodes=args.nodes) as s:
            s._load_plugin(store_type=args.store, nodes=args.nodes)
            t = s.token_create_admin()
            if t:
                data = {
                    'token': t.encode('utf-8'),
                }
                with open(args.token_create_admin, 'w') as f:
                    f.write(yaml.dump(data, default_flow_style=False))

                logger.info('token config generated: {}'.format(args.token_create_admin))
            else:
                logger.error('token not created')

if __name__ == "__main__":
    main()
