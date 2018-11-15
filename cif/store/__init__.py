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
from csirtg_indicator import Indicator
import zmq
import time
from base64 import b64encode

from cifsdk.msg import Msg
import cif.store
from cif.constants import STORE_ADDR, PYVERSION
from cifsdk.constants import REMOTE_ADDR, CONFIG_PATH
from cifsdk.exceptions import AuthError, InvalidSearch
from cif.exceptions import StoreLockError
from csirtg_indicator import InvalidIndicator
from cifsdk.utils import setup_logging, get_argument_parser, setup_signals
from types import GeneratorType
import traceback
import binascii
from base64 import b64decode

if PYVERSION > 2:
    basestring = (str, bytes)

MOD_PATH = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
STORE_PATH = os.path.join(MOD_PATH, "store")
RCVTIMEO = 5000
SNDTIMEO = 2000
LINGER = 3
STORE_DEFAULT = os.environ.get('CIF_STORE_STORE', 'sqlite')
STORE_PLUGINS = ['cif.store.dummy', 'cif.store.sqlite', 'cif.store.elasticsearch']
CREATE_QUEUE_FLUSH = os.environ.get('CIF_STORE_QUEUE_FLUSH', 5)   # seconds to flush the queue [interval]
CREATE_QUEUE_LIMIT = os.environ.get('CIF_STORE_QUEUE_LIMIT', 250)  # num of records before we start throttling a token
# seconds of in-activity before we remove from the penalty box
CREATE_QUEUE_TIMEOUT = os.environ.get('CIF_STORE_TIMEOUT', 300)

# queue max to flush before we hit CIF_STORE_QUEUE_FLUSH mark
CREATE_QUEUE_MAX = os.environ.get('CIF_STORE_QUEUE_MAX', 1000)

MORE_DATA_NEEDED = -2

TRACE = os.environ.get('CIF_STORE_TRACE')
    
logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)

if TRACE in [1, '1']:
   logger.setLevel(logging.DEBUG)


class Store(multiprocessing.Process):
    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        return False

    def __init__(self, store_type=STORE_DEFAULT, store_address=STORE_ADDR, **kwargs):
        multiprocessing.Process.__init__(self)

        self.store_addr = store_address
        self.store = store_type
        self.kwargs = kwargs
        self.exit = multiprocessing.Event()
        self.create_queue = {}
        self.create_queue_flush = CREATE_QUEUE_FLUSH
        self.create_queue_limit = CREATE_QUEUE_LIMIT
        self.create_queue_wait = CREATE_QUEUE_TIMEOUT
        self.create_queue_max = CREATE_QUEUE_MAX
        self.create_queue_count = 0

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

        last_flushed = time.time()
        while not self.exit.is_set():
            try:
                m = dict(poller.poll(1000))
            except SystemExit or KeyboardInterrupt:
                break

            if self.router in m:
                m = Msg().recv(self.router)
                self.handle_message(m)

            if len(self.create_queue) > 0 and ((time.time() - last_flushed) > self.create_queue_flush) or (self.create_queue_count >= self.create_queue_max):
                self._flush_create_queue()
                for t in list(self.create_queue):
                    self.create_queue[t]['messages'] = []

                    # if we've not seen activity in 300s reset the counter
                    if self.create_queue[t]['count'] > 0:
                        if (time.time() - self.create_queue[t]['last_activity']) > self.create_queue_wait:
                            logger.debug('pruning {} from create_queue'.format(t))
                            del self.create_queue[t]

                self.create_queue_count = 0
                last_flushed = time.time()

    def terminate(self):
        self.exit.set()

    def handle_message(self, m):
        err = None
        id, client_id, token, mtype, data = m

        if isinstance(data, basestring):
            try:
                data = json.loads(data)
            except ValueError as e:
                logger.error(e)
                data = json.dumps({"status": "failed"})
                Msg(id=id, client_id=client_id, mtype=mtype, data=data).send(self.router)
                return

        handler = getattr(self, "handle_" + mtype)
        if not handler:
            logger.error('message type {0} unknown'.format(mtype))
            Msg(id=id, data='0')

        try:
            rv = handler(token, data, id=id, client_id=client_id)
            if rv == MORE_DATA_NEEDED:
                rv = {"status": "success", "data": '1'}
            else:
                rv = {"status": "success", "data": rv}

        except AuthError as e:
            logger.error(e)
            err = 'unauthorized'

        except InvalidSearch as e:
            err = 'invalid search'

        except InvalidIndicator as e:
            logger.error(data)
            logger.error(e)
            traceback.print_exc()
            err = 'invalid indicator {}'.format(e)

        except StoreLockError as e:
            logger.error(e)
            traceback.print_exc()
            err = 'busy'

        except Exception as e:
            logger.error(e)
            traceback.print_exc()
            err = 'unknown failure'

        if err:
            rv = {'status': 'failed', 'message': err}

        try:
            data = json.dumps(rv)
        except Exception as e:
            logger.error(e)
            traceback.print_exc()
            data = json.dumps({'status': 'failed', 'message': 'feed to large, retry the query'})

        Msg(id=id, client_id=client_id, mtype=mtype, data=data).send(self.router)

        if not err:
            self.store.tokens.update_last_activity_at(token, arrow.utcnow().datetime)

    def _flush_create_queue(self):
        for t in self.create_queue:
            if len(self.create_queue[t]['messages']) == 0:
                continue

            logger.debug('flushing queue...')
            data = [msg[0] for _, _, msg in self.create_queue[t]['messages']]
            _t = self.store.tokens.write(t)

            try:
                start_time = time.time()
                logger.info('attempting to insert %d indicators..', len(data))

                # this will raise AuthError if the groups don't match
                if isinstance(data, dict):
                    data = [data]

                for i in data:
                    if not i.get('group'):
                        i['group'] = 'everyone'

                    if not i.get('provider') or i['provider'] == '':
                        i['provider'] = _t['username']

                    if i['group'] not in _t['groups']:
                        raise AuthError('unable to write to %s' % i['group'])

                    if not i.get('tags'):
                        i['tags'] = ['suspicious']

                    if i.get('message'):
                        try:
                            i['message'] = str(b64decode(data['message']))
                        except (TypeError, binascii.Error) as e:
                            pass

                n = self.store.indicators.upsert(_t, data)

                t_time = time.time() - start_time
                logger.info('actually inserted %d indicators.. took %0.2f seconds (%0.2f/sec)', n, t_time, (n / t_time))

                if n == 0:
                    rv = {'status': 'failed', 'message': 'invalid indicator'}
                else:
                    rv = {"status": "success", "data": n}

            except AuthError as e:
                rv = {'status': 'failed', 'message': 'unauthorized'}

            except StoreLockError:
                rv = {'status': 'failed', 'message': 'busy'}

            for id, client_id, _ in self.create_queue[t]['messages']:
                Msg(id=id, client_id=client_id, mtype=Msg.INDICATORS_CREATE, data=rv)

            if rv['status'] == 'success':
                self.store.tokens.update_last_activity_at(t, arrow.utcnow().datetime)

            logger.debug('queue flushed..')

    def handle_indicators_delete(self, token, data=None, id=None, client_id=None):
        t = self.store.tokens.admin(token)
        return self.store.indicators.delete(t, data=data, id=id)

    def handle_indicators_create(self, token, data, id=None, client_id=None, flush=False):
        # this will raise AuthError if false
        t = self.store.tokens.write(token)

        if len(data) > 1 or t['username'] == 'admin':
            start_time = time.time()
            logger.info('attempting to insert %d indicators..', len(data))

            # this will raise AuthError if the groups don't match
            if isinstance(data, dict):
                data = [data]

            for i in data:
                if not i.get('group'):
                    i['group'] = 'everyone'

                if not i.get('provider') or i['provider'] == '':
                    i['provider'] = t['username']

                if i['group'] not in t['groups']:
                    raise AuthError('unable to write to %s' % i['group'])

                if not i.get('tags'):
                    i['tags'] = ['suspicious']

                if i.get('message'):
                    try:
                        i['message'] = str(b64decode(data['message']))
                    except (TypeError, binascii.Error) as e:
                        pass

            n = self.store.indicators.upsert(t, data, flush=flush)

            t = time.time() - start_time
            logger.info('actually inserted %d indicators.. took %0.2f seconds (%0.2f/sec)', n, t, (n/t))

            return n

        data = data[0]
        if data['group'] not in t['groups']:
            raise AuthError('unauthorized to write to group: %s' % data['group'])

        if data.get('message'):
            try:
                data['message'] = str(b64decode(data['message']))
            except (TypeError, binascii.Error) as e:
                pass

        if not self.create_queue.get(token):
            self.create_queue[token] = {'count': 0, "messages": []}

        self.create_queue[token]['count'] += 1
        self.create_queue_count += 1
        self.create_queue[token]['last_activity'] = time.time()

        self.create_queue[token]['messages'].append((id, client_id, [data]))

        return MORE_DATA_NEEDED

    def _log_search(self, t, data):
        if not data.get('indicator'):
            return

        if data.get('nolog') in ['1', 'True', 1, True]:
            return

        if '*' in data.get('indicator'):
            return

        if '%' in data.get('indicator'):
            return

        ts = arrow.utcnow().format('YYYY-MM-DDTHH:mm:ss.SSZ')
        s = Indicator(
            indicator=data['indicator'],
            tlp='amber',
            confidence=10,
            tags='search',
            provider=t['username'],
            firsttime=ts,
            lasttime=ts,
            reporttime=ts,
            group=t['groups'][0],
            count=1,
        )
        self.store.indicators.upsert(t, [s.__dict__()])

    def handle_indicators_search(self, token, data, **kwargs):
        t = self.store.tokens.read(token)

        if PYVERSION == 2:
            if data.get('indicator'):
                if isinstance(data['indicator'], str):
                    data['indicator'] = unicode(data['indicator'])

        if not data.get('reporttime'):
            if data.get('days'):
                now = arrow.utcnow()
                data['reporttimeend'] = '{0}Z'.format(now.format('YYYY-MM-DDTHH:mm:ss'))
                now = now.replace(days=-int(data['days']))
                data['reporttime'] = '{0}Z'.format(now.format('YYYY-MM-DDTHH:mm:ss'))

            if data.get('hours'):
                now = arrow.utcnow()
                data['reporttimeend'] = '{0}Z'.format(now.format('YYYY-MM-DDTHH:mm:ss'))
                now = now.replace(hours=-int(data['hours']))
                data['reporttime'] = '{0}Z'.format(now.format('YYYY-MM-DDTHH:mm:ss'))

        s = time.time()

        self._log_search(t, data)

        try:
            x = self.store.indicators.search(t, data)
            logger.debug('done')
        except Exception as e:
            logger.error(e)

            if logger.getEffectiveLevel() == logging.DEBUG:
                logger.error(traceback.print_exc())

            raise InvalidSearch('invalid search')

        logger.debug('%s' % (time.time() - s))

        # for xx in x:
        #     if xx.get('message'):
        #         xx['message'] = b64encode(xx['message']).encode('utf-8')

        return x

    def handle_ping(self, token, data='[]', **kwargs):
        logger.debug('handling ping message')
        return self.store.ping(token)

    def handle_ping_write(self, token, data='[]', **kwargs):
        logger.debug('handling ping write')
        return self.store.tokens.write(token)

    def handle_tokens_search(self, token, data, **kwargs):
        if self.store.tokens.admin(token):
            logger.debug('tokens_search')
            return self.store.tokens.search(data)

        raise AuthError('invalid token')

    def handle_tokens_create(self, token, data, **kwargs):
        if self.store.tokens.admin(token):
            logger.debug('tokens_create')
            return self.store.tokens.create(data)

        raise AuthError('invalid token')

    def handle_tokens_delete(self, token, data, **kwargs):
        if self.store.tokens.admin(token):
            return self.store.tokens.delete(data)

        raise AuthError('invalid token')

    def handle_token_write(self, token, data=None, **kwargs):
        return self.store.tokens.write(token)

    def handle_tokens_edit(self, token, data, **kwargs):
        if self.store.tokens.admin(token):
            return self.store.tokens.edit(data)

        raise AuthError('invalid token')

    def token_create_admin(self, token=None, groups=['everyone']):
        logger.info('testing for tokens...')
        if not self.store.tokens.admin_exists():
            logger.info('admin token does not exist, generating..')
            rv = self.store.tokens.create({
                'username': u'admin',
                'groups': groups,
                'read': u'1',
                'write': u'1',
                'admin': u'1',
                'token': token
            })
            logger.info('admin token created: {}'.format(rv['token']))
            return rv['token']

        logger.info('admin token exists...')

    def token_create_smrt(self, token=None, groups=['everyone']):
        logger.info('generating smrt token')
        rv = self.store.tokens.create({
            'username': u'csirtg-smrt',
            'groups': groups,
            'write': u'1',
            'token': token
        })
        logger.info('smrt token created: {}'.format(rv['token']))
        return rv['token']

    def token_create_hunter(self, token=None, groups=['everyone']):
        logger.info('generating hunter token')
        rv = self.store.tokens.create({
            'username': u'hunter',
            'groups': groups,
            'write': u'1',
            'token': token
        })
        logger.info('hunter token created: {}'.format(rv['token']))
        return rv['token']

    def token_create_httpd(self, token=None, groups=['everyone']):
        logger.info('generating httpd token')
        rv = self.store.tokens.create({
            'username': u'httpd',
            'groups': groups,
            'read': u'1',
            'token': token
        })
        logger.info('httpd token created: {}'.format(rv['token']))
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

    p.add_argument('--nodes')

    p.add_argument('--config', help='specify config path [default %(default)s]', default=CONFIG_PATH)

    p.add_argument('--token-create-admin', help='generate an admin token', action="store_true")
    p.add_argument('--token-create-smrt', action="store_true")
    p.add_argument('--token-create-smrt-remote', default=REMOTE_ADDR)
    p.add_argument('--token-create-hunter', action="store_true")
    p.add_argument('--token-create-httpd', action="store_true")

    p.add_argument('--config-path', help='store the token as a config')
    p.add_argument('--token', help='specify the token to use', default=None)
    p.add_argument('--token-groups', help="specify groups associated with token [default %(default)s]'", default='everyone')

    p.add_argument('--remote', help='specify remote')

    args = p.parse_args()

    groups = args.token_groups.split(',')

    setup_logging(args)
    logger = logging.getLogger(__name__)
    logger.info('loglevel is: {}'.format(logging.getLevelName(logger.getEffectiveLevel())))

    setup_signals(__name__)

    if not args.token_create_smrt and not args.token_create_admin and not args.token_create_hunter and not \
            args.token_create_httpd:
        logger.error('missing required arguments, see -h for more information')
        raise SystemExit

    if args.token_create_smrt:
        with Store(store_type=args.store, nodes=args.nodes) as s:
            s._load_plugin(store_type=args.store, nodes=args.nodes)

            t = s.token_create_smrt(token=args.token, groups=groups)
            if t:
                if PYVERSION == 2:
                    t = t.encode('utf-8')

                data = {
                    'token': t,
                }
                if args.remote:
                    data['remote'] = args.remote

                if args.config_path:
                    with open(args.config_path, 'w') as f:
                        f.write(yaml.dump(data, default_flow_style=False))

                logger.info('token config generated: {}'.format(args.token_create_smrt))
            else:
                logger.error('token not created')

    if args.token_create_hunter:
        with Store(store_type=args.store, nodes=args.nodes) as s:
            s._load_plugin(store_type=args.store, nodes=args.nodes)
            t = s.token_create_hunter(token=args.token, groups=groups)
            if t:
                if PYVERSION == 2:
                    t = t.encode('utf-8')

                data = {
                    'hunter_token': t,
                }

                if args.config_path:
                    with open(args.config_path, 'w') as f:
                        f.write(yaml.dump(data, default_flow_style=False))

                logger.info('token config generated: {}'.format(args.token_create_hunter))
            else:
                logger.error('token not created')

    if args.token_create_admin:
        with Store(store_type=args.store, nodes=args.nodes) as s:
            s._load_plugin(store_type=args.store, nodes=args.nodes)
            t = s.token_create_admin(token=args.token, groups=groups)
            if t:
                if PYVERSION == 2:
                    t = t.encode('utf-8')

                data = {
                    'token': t,
                }

                if args.config_path:
                    with open(args.config_path, 'w') as f:
                        f.write(yaml.dump(data, default_flow_style=False))

                logger.info('token config generated: {}'.format(args.token_create_admin))
            else:
                logger.error('token not created')

    if args.token_create_httpd:
        with Store(store_type=args.store, nodes=args.nodes) as s:
            s._load_plugin(store_type=args.store, nodes=args.nodes)
            t = s.token_create_httpd(token=args.token, groups=groups)
            if t:
                if PYVERSION == 2:
                    t = t.encode('utf-8')

                data = {
                    'token': t,
                }

                if args.config_path:
                    with open(args.config_path, 'w') as f:
                        f.write(yaml.dump(data, default_flow_style=False))

                logger.info('token config generated: {}'.format(args.token_create_httpd))
            else:
                logger.error('token not created')

if __name__ == "__main__":
    main()
