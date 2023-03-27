#!/usr/bin/env python

import ujson as json
import logging
import textwrap
import traceback
from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter
from time import sleep
import zmq
import os
from cif.constants import ROUTER_ADDR, STORE_ADDR, HUNTER_ADDR, GATHERER_ADDR, GATHERER_SINK_ADDR, HUNTER_SINK_ADDR, \
            RUNTIME_PATH, AUTH_ENABLED, AUTH_ADDR, CTRL_ADDR
from cifsdk.constants import CONFIG_PATH
from cifsdk.utils import setup_logging, get_argument_parser, setup_signals, setup_runtime_path, read_config
from cif.hunter import Hunter
from cif.store import Store
from cif.gatherer import Gatherer
import time
import multiprocessing as mp
from cifsdk.msg import Msg
from cif.auth import Auth
from cif.utils import strtobool

AUTH_TYPE = 'cif_store'
AUTH_PLUGINS = ['cif.auth.cif_store']
if AUTH_ENABLED not in [1, '1', 'True', True]:
    AUTH_ENABLED = False

HUNTER_THREADS = os.getenv('CIF_HUNTER_THREADS', 0)
HUNTER_ADVANCED = os.getenv('CIF_HUNTER_ADVANCED', 0)
GATHERER_THREADS = os.getenv('CIF_GATHERER_THREADS', 2)
STORE_DEFAULT = 'sqlite'
STORE_PLUGINS = ['cif.store.dummy', 'cif.store.sqlite', 'cif.store.elasticsearch']

ZMQ_HWM = 1000000
ZMQ_SNDTIMEO = 5000
ZMQ_RCVTIMEO = 5000
FRONTEND_TIMEOUT = os.environ.get('CIF_FRONTEND_TIMEOUT', 100)
BACKEND_TIMEOUT = os.environ.get('CIF_BACKEND_TIMEOUT', 10)

HUNTER_TOKEN = os.environ.get('CIF_HUNTER_TOKEN', None)

CONFIG_PATH = os.environ.get('CIF_ROUTER_CONFIG_PATH', 'cif-router.yml')
if not os.path.isfile(CONFIG_PATH):
    CONFIG_PATH = os.environ.get('CIF_ROUTER_CONFIG_PATH', os.path.join(os.path.expanduser('~'), 'cif-router.yml'))

STORE_DEFAULT = os.getenv('CIF_STORE_STORE', STORE_DEFAULT)
STORE_NODES = os.getenv('CIF_STORE_NODES')

PIDFILE = os.getenv('CIF_ROUTER_PIDFILE', '{}/cif_router.pid'.format(RUNTIME_PATH))

TRACE = strtobool(os.environ.get('CIF_ROUTER_TRACE', False))

logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)

if TRACE:
    logger.setLevel(logging.DEBUG)


class Router(object):

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        return self

    def __init__(self, listen=ROUTER_ADDR, hunter=HUNTER_ADDR, store_type=STORE_DEFAULT, store_address=STORE_ADDR,
                 store_nodes=None, hunter_token=HUNTER_TOKEN, hunter_threads=HUNTER_THREADS,
                 gatherer_threads=GATHERER_THREADS, auth_required=AUTH_ENABLED, auth_address=AUTH_ADDR, 
                 auth_type=AUTH_TYPE, test=False):

        self.logger = logging.getLogger(__name__)

        self.context = zmq.Context()

        if test:
            return

        self.store_s = self.context.socket(zmq.DEALER)
        self.store_s.bind(store_address)

        self.store_p = None
        self._init_store(self.context, store_address, store_type, nodes=store_nodes)

        self.gatherer_s = self.context.socket(zmq.PUSH)
        self.gatherer_sink_s = self.context.socket(zmq.PULL)
        self.gatherer_s.bind(GATHERER_ADDR)
        self.gatherer_sink_s.bind(GATHERER_SINK_ADDR)
        self.gatherers = []
        self._init_gatherers(gatherer_threads)

        self.auth_required = auth_required

        self.hunter_sink_s = self.context.socket(zmq.ROUTER)
        self.hunter_sink_s.bind(HUNTER_SINK_ADDR)

        self.hunter_token_dict = None
        self.hunter_token_dict_as_str = ''
        self.ctrl_sink_s = self.context.socket(zmq.PULL)
        self.ctrl_sink_s.SNDTIMEO = ZMQ_SNDTIMEO
        self.ctrl_sink_s.set_hwm(ZMQ_HWM)
        self.ctrl_sink_s.connect(CTRL_ADDR)

        self.hunters = []
        self.hunters_s = None
        if hunter_threads and int(hunter_threads):
            self.hunters_s = self.context.socket(zmq.PUSH)
            self.logger.debug('binding hunter from router: {}'.format(hunter))
            self.hunters_s.bind(hunter)
            self._init_hunters(hunter_threads, hunter_token)

        self.auth_s = None
        self.auth_p = None
        self.logger.info('auth required is set to {}'.format(auth_required))
        if self.auth_required:
            self.auth_s = self.context.socket(zmq.DEALER)
            self.auth_s.bind(auth_address)
            self._init_auth(auth_address, auth_type)

        self.logger.info('launching frontend...')
        self.frontend_s = self.context.socket(zmq.ROUTER)
        self.frontend_s.set_hwm(ZMQ_HWM)
        self.frontend_s.bind(listen)

        self.count = 0
        self.count_start = time.time()

        self.poller = zmq.Poller()
        self.poller_backend = zmq.Poller()

        self.terminate = False

    def _init_hunters(self, threads, token):
        self.logger.info('launching hunters...')
        for n in range(int(threads)):
            p = mp.Process(target=Hunter(token=token).start)
            p.start()
            self.hunters.append(p)

    def _init_gatherers(self, threads):
        self.logger.info('launching gatherers...')
        for n in range(int(threads)):
            p = mp.Process(target=Gatherer().start)
            p.start()
            self.gatherers.append(p)

    def _init_store(self, context, store_address, store_type, nodes=False):
        self.logger.info('launching store...')
        p = mp.Process(target=Store(store_address=store_address, store_type=store_type, nodes=nodes).start)
        p.start()
        self.store_p = p

    def _init_auth(self, auth_address, auth_type):
        self.logger.info('launching auth...')
        p = mp.Process(target=Auth(auth_address=auth_address, auth_type=auth_type).start)
        p.start()
        self.auth_p = p

    def stop(self):
        self.terminate = True
        self.logger.info('stopping hunters..')
        for h in self.hunters:
            h.terminate()

        self.logger.info('stopping gatherers')
        for g in self.gatherers:
            g.terminate()

        self.logger.info('stopping auth..')
        self.auth_p.terminate()

        self.logger.info('stopping store..')
        self.store_p.terminate()

        sleep(0.01)

    def start(self):
        self.logger.debug('starting loop')

        self.poller_backend.register(self.ctrl_sink_s, zmq.POLLIN)
        self.poller_backend.register(self.hunter_sink_s, zmq.POLLIN)
        self.poller_backend.register(self.gatherer_sink_s, zmq.POLLIN)
        self.poller.register(self.store_s, zmq.POLLIN)
        if self.auth_required:
            self.poller.register(self.auth_s, zmq.POLLIN)
        self.poller.register(self.frontend_s, zmq.POLLIN)

        # we use this instead of a loop so we can make sure to get front end queries as they come in
        # that way hunters don't over burden the store, think of it like QoS
        # it's weighted so front end has a higher chance of getting a faster response
        while not self.terminate:
            items = dict(self.poller_backend.poll(BACKEND_TIMEOUT))

            if self.gatherer_sink_s in items and items[self.gatherer_sink_s] == zmq.POLLIN:
                self.handle_message_gatherer(self.gatherer_sink_s)

            if self.hunter_sink_s in items and items[self.hunter_sink_s] == zmq.POLLIN:
                self.handle_message_backend_request(self.hunter_sink_s)

            # handle recv hunter token as data one time, then save/shutdown this sink
            if not self.hunter_token_dict and self.ctrl_sink_s and self.ctrl_sink_s in items and items[self.ctrl_sink_s] == zmq.POLLIN:
                self.logger.debug('Recving hunter token from store...')
                self.hunter_token_dict_as_str = self.ctrl_sink_s.recv_string()
                self.hunter_token_dict = json.loads(self.hunter_token_dict_as_str)
                self.ctrl_sink_s.close()
                self.poller_backend.unregister(self.ctrl_sink_s)
                self.ctrl_sink_s = None

            items = dict(self.poller.poll(FRONTEND_TIMEOUT))

            if self.frontend_s in items and items[self.frontend_s] == zmq.POLLIN:
                if self.auth_required:
                    self.handle_message_auth_request(self.frontend_s)
                else:
                    self.handle_message_backend_request(self.frontend_s)

            if self.auth_required and self.auth_s in items and items[self.auth_s] == zmq.POLLIN:
                self.handle_message_auth_response(self.auth_s)

            if self.store_s in items and items[self.store_s] == zmq.POLLIN:
                self.handle_message_response(self.store_s)


    def _log_counter(self):
        self.count += 1
        if (self.count % 100) == 0:
            t = (time.time() - self.count_start)
            n = self.count / t
            self.logger.info('processing {} msgs per {} sec'.format(round(n, 2), round(t, 2)))
            self.count = 0
            self.count_start = time.time()

    def handle_message_backend_request(self, s):
        # if something comes directly to the backend, that implies it was an internal request
        # such as from a hunter (or no auth enabled). therefore, use hunter token for request
        if not self.hunter_token_dict:
            # this is just needed at startup hopefully in case we get a backend request
            # before ctrl_sink has received hunter token. if this msg keeps appearing
            # 5-10 secs after startup, there may be an issue
            self.logger.info('Got backend request before hunter token was ready. Skipping...')
            return
        id, token, mtype, data = Msg().recv(s)
        token = self.hunter_token_dict_as_str
        self.handle_message_request(id, token, mtype, data)

    def handle_message_request(self, id, token, mtype, data):
        handler = self.handle_message_default
        if mtype in ['indicators_create', 'indicators_search', 'ping_write']:
            handler = getattr(self, "handle_" + mtype)

        try:
            handler(id, mtype, token, data)
        except Exception as e:
            self.logger.error(e)

        self._log_counter()

    def handle_message_default(self, id, mtype, token, data='[]'):
        Msg(id=id, mtype=mtype, token=token, data=data).send(self.store_s)

    def handle_ping_write(self, id, mtype, token, data):
        # format the token as is expected by cifsdk for a data field resp
        token = json.loads(token)
        data = json.dumps({ 'status': 'success', 'data': token })
        # respond to appropriate socket
        if token.get('username') == self.hunter_token_dict.get('username'):
            Msg(id=id, mtype=mtype, data=data).send(self.hunter_sink_s)
        else:
            Msg(id=id, mtype=mtype, data=data).send(self.frontend_s)

    def handle_indicators_search(self, id, mtype, token, data):
        self.handle_message_default(id, mtype, token, data)

        if self.hunters:
            Msg(id=id, mtype=mtype, token=token, data=data).send(self.hunters_s)

    def handle_indicators_create(self, id, mtype, token, data):
        Msg(id=id, mtype=mtype, token=token, data=data).send(self.gatherer_s)

    def handle_message_response(self, s):
        # re-routing from store to frontend or hunter_sink (as based on the username for a source)
        id, token, mtype, data = Msg().recv(s)
        token = json.loads(token)
        if token.get('username') == self.hunter_token_dict.get('username'):
            Msg(id=id, mtype=mtype, data=data).send(self.hunter_sink_s)
        else:
            Msg(id=id, mtype=mtype, data=data).send(self.frontend_s)

    def handle_message_gatherer(self, s):
        id, token, mtype, data = Msg().recv(s)

        Msg(id=id, mtype=mtype, token=token, data=data).send(self.store_s)

        if self.hunters:
            Msg(id=id, mtype=mtype, token=token, data=data).send(self.hunters_s)

    def handle_message_auth_request(self, s):
        id, token, mtype, data = Msg().recv(s)
        Msg(id=id, mtype=mtype, token=token, data=data).send(self.auth_s)

    def handle_message_auth_response(self, s):
        id, token, mtype, data = Msg().recv(s)

        try:
            data_dict = json.loads(data)
        except Exception as e:
            # this can happen if invalid json passed in request
            # e.g., PATCH to /tokens with { "token": "longtokenhere_followedbymissingdblquote, "groups": ["everyone"] }
            data_dict = { 'status': 'failed', 'message': 'invalid JSON'}
            logger.error('Could not decode auth resp data {}. Error {}'.format(data, e))
            data = json.dumps(data_dict)

        # route based on resp
        if isinstance(data_dict, dict) and data_dict.get('status') == 'failed':
            # route auth failure back to frontend
            Msg(id=id, mtype=mtype, data=data).send(self.frontend_s)
        else:
            # if we get here, authN/authZ succeeded
            self.handle_message_request(id, token, mtype, data)

def main():
    p = get_argument_parser()
    p = ArgumentParser(
        description=textwrap.dedent('''\
        Env Variables:
            CIF_RUNTIME_PATH
            CIF_ROUTER_CONFIG_PATH
            CIF_ROUTER_ADDR
            CIF_HUNTER_ADDR
            CIF_HUNTER_TOKEN
            CIF_HUNTER_THREADS
            CIF_GATHERER_THREADS
            CIF_STORE_ADDR

        example usage:
            $ cif-router --listen 0.0.0.0 -d
        '''),
        formatter_class=RawDescriptionHelpFormatter,
        prog='cif-router',
        parents=[p]
    )

    p.add_argument('--config', help='specify config path [default: %(default)s', default=CONFIG_PATH)
    p.add_argument('--listen', help='address to listen on [default: %(default)s]', default=ROUTER_ADDR)

    p.add_argument('--gatherer-threads', help='specify number of gatherer threads to use [default: %(default)s]',
                   default=GATHERER_THREADS)

    p.add_argument('--hunter', help='address hunters listen on on [default: %(default)s]', default=HUNTER_ADDR)
    p.add_argument('--hunter-token', help='specify token for hunters to use [default: %(default)s]',
                   default=HUNTER_TOKEN)
    p.add_argument('--hunter-threads', help='specify number of hunter threads to use [default: %(default)s]',
                   default=HUNTER_THREADS)

    p.add_argument("--store-address", help="specify the store address cif-router is listening on[default: %("
                                           "default)s]", default=STORE_ADDR)

    p.add_argument("--store", help="specify a store type {} [default: %(default)s]".format(', '.join(STORE_PLUGINS)),
                   default=STORE_DEFAULT)

    p.add_argument('--store-nodes', help='specify storage nodes address [default: %(default)s]', default=STORE_NODES)

    p.add_argument('--logging-ignore', help='set logging to WARNING for specific modules')

    p.add_argument('--pidfile', help='specify pidfile location [default: %(default)s]', default=PIDFILE)

    args = p.parse_args()
    setup_logging(args)
    logger = logging.getLogger(__name__)
    logger.info('loglevel is: {}'.format(logging.getLevelName(logger.getEffectiveLevel())))

    if args.logging_ignore:
        to_ignore = args.logging_ignore.split(',')

        for i in to_ignore:
            logging.getLogger(i).setLevel(logging.WARNING)

    o = read_config(args)
    options = vars(args)
    for v in options:
        if options[v] is None:
            options[v] = o.get(v)

    setup_runtime_path(args.runtime_path)
    setup_signals(__name__)

    # http://stackoverflow.com/a/789383/7205341
    pid = str(os.getpid())
    logger.debug("pid: %s" % pid)

    if os.path.isfile(args.pidfile):
        logger.critical("%s already exists, exiting" % args.pidfile)
        raise SystemExit

    try:
        pidfile = open(args.pidfile, 'w')
        pidfile.write(pid)
        pidfile.close()
    except PermissionError as e:
        logger.error('unable to create pid %s' % args.pidfile)

    with Router(listen=args.listen, hunter=args.hunter, store_type=args.store, store_address=args.store_address,
                store_nodes=args.store_nodes, hunter_token=args.hunter_token, hunter_threads=args.hunter_threads,
                gatherer_threads=args.gatherer_threads) as r:
        try:
            logger.info('starting router..')
            r.start()

        except KeyboardInterrupt:
            # todo - signal to threads to shut down and wait for them to finish
            logger.info('shutting down via SIGINT...')

        except SystemExit:
            logger.info('shutting down via SystemExit...')

        except Exception as e:
            logger.critical(e)
            traceback.print_exc()

        r.stop()

    logger.info('Shutting down')
    if os.path.isfile(args.pidfile):
        os.unlink(args.pidfile)

if __name__ == "__main__":
    main()
