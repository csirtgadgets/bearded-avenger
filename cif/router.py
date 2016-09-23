#!/usr/bin/env python

import ujson as json
import logging
import textwrap
import traceback
from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter
from pprint import pprint

import zmq
from zmq.eventloop import ioloop
import os
from cif.constants import ROUTER_ADDR, STORE_ADDR, HUNTER_ADDR, GATHERER_ADDR, GATHERER_SINK_ADDR, HUNTER_SINK_ADDR
from cifsdk.constants import CONFIG_PATH
from cifsdk.utils import setup_logging, get_argument_parser, setup_signals, zhelper, setup_runtime_path, read_config
from csirtg_indicator import Indicator
import threading
from cif.hunter import Hunter
from cif.store import Store
from cif.gatherer import Gatherer
import time
import multiprocessing as mp

HUNTER_MIN_CONFIDENCE = 2
HUNTER_THREADS = os.getenv('CIF_HUNTER_THREADS', 2)
GATHERER_THREADS = os.getenv('CIF_GATHERER_THREADS', 4)
STORE_DEFAULT = 'sqlite'
STORE_PLUGINS = ['cif.store.dummy', 'cif.store.sqlite', 'cif.store.elasticsearch', 'cif.store.rdflib']

ZMQ_HWM = 1000000
ZMQ_SNDTIMEO = 5000
ZMQ_RCVTIMEO = 5000
FRONTEND_TIMEOUT = 1
BACKEND_TIMEOUT = 1

HUNTER_TOKEN = os.environ.get('CIF_HUNTER_TOKEN', None)

CONFIG_PATH = os.environ.get('CIF_ROUTER_CONFIG_PATH', 'cif-router.yml')
if not os.path.isfile(CONFIG_PATH):
    CONFIG_PATH = os.environ.get('CIF_ROUTER_CONFIG_PATH', os.path.join(os.path.expanduser('~'), 'cif-router.yml'))

STORE_DEFAULT = os.getenv('CIF_STORE_STORE', STORE_DEFAULT)
STORE_NODES = os.getenv('CIF_STORE_NODES')


class Router(object):

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        return self

    def __init__(self, listen=ROUTER_ADDR, hunter=HUNTER_ADDR, store_type=STORE_DEFAULT, store_address=STORE_ADDR,
                 store_nodes=None, p2p=False, hunter_token=HUNTER_TOKEN, hunter_threads=HUNTER_THREADS,
                 gatherer_threads=GATHERER_THREADS, test=False):

        self.logger = logging.getLogger(__name__)

        self.context = zmq.Context()

        if test:
            return

        self.store_s = self.context.socket(zmq.DEALER)
        self.store_s.bind(store_address)

        self._init_store(self.context, store_address, store_type, nodes=store_nodes)

        self.gatherer_s = self.context.socket(zmq.PUSH)
        self.gatherer_sink_s = self.context.socket(zmq.PULL)
        self.gatherer_s.bind(GATHERER_ADDR)
        self.gatherer_sink_s.bind(GATHERER_SINK_ADDR)
        self._init_gatherers(gatherer_threads)

        self.hunter_sink_s = self.context.socket(zmq.ROUTER)
        self.hunter_sink_s.bind(HUNTER_SINK_ADDR)

        if int(hunter_threads):
            self.hunters_s = self.context.socket(zmq.PUSH)
            self.logger.debug('binding hunter: {}'.format(hunter))
            self.hunters_s.bind(hunter)

            self.hunters = []
            self._init_hunters(hunter_threads, hunter_token)
        else:
            self.hunters_s = None

        self.p2p = p2p
        if self.p2p:
            self._init_p2p()
            self.p2p

        self.logger.info('launching frontend...')
        self.frontend_s = self.context.socket(zmq.ROUTER)
        self.frontend_s.set_hwm(ZMQ_HWM)
        self.frontend_s.bind(listen)

        self.count = 0
        self.count_start = time.time()

        self.poller = zmq.Poller()
        self.poller_backend = zmq.Poller()

        self.terminate = False

    def _init_p2p(self):
        self.logger.info('enabling p2p..')
        from cif.p2p import Client as p2pcli
        self.p2p = p2pcli(channel='CIF')
        p2p_pipe = zhelper.zthread_fork(self.context, self.p2p.start)
        self.p2p = p2p_pipe

    def _init_hunters(self, threads, token):
        self.logger.info('launching hunters...')
        for n in range(int(threads)):
            p = mp.Process(target=Hunter(token=token).start)
            p.start()

    def _init_gatherers(self, threads):
        self.logger.info('launching gatherers...')
        for n in range(int(threads)):
            p = mp.Process(target=Gatherer().start)
            p.start()

    def _init_store(self, context, store_address, store_type, nodes=False):
        self.logger.info('launching store...')
        p = mp.Process(target=Store(store_address=store_address, store_type=store_type, nodes=nodes).start)
        p.start()

    def stop(self):
        self.terminate = True
        if self.p2p:
            self.p2p.send("$$STOP".encode('utf_8'))

    def start(self):
        self.logger.debug('starting loop')

        self.poller_backend.register(self.hunter_sink_s, zmq.POLLIN)
        self.poller_backend.register(self.gatherer_sink_s, zmq.POLLIN)
        self.poller.register(self.store_s, zmq.POLLIN)
        self.poller.register(self.frontend_s, zmq.POLLIN)

        # we use this instead of a loop so we can make sure to get front end queries as they come in
        # that way hunters don't over burden the store, think of it like QoS
        # it's weighted so front end has a higher chance of getting a faster response
        terminated = self.terminate
        while not terminated:
            items = dict(self.poller.poll(FRONTEND_TIMEOUT))

            if self.frontend_s in items and items[self.frontend_s] == zmq.POLLIN:
                self.handle_message(self.frontend_s)

            if self.store_s in items and items[self.store_s] == zmq.POLLIN:
                self.handle_message_store(self.store_s)

            items = dict(self.poller_backend.poll(BACKEND_TIMEOUT))

            if self.gatherer_sink_s in items and items[self.gatherer_sink_s] == zmq.POLLIN:
                self.handle_message_gatherer(self.gatherer_sink_s)

            if self.hunter_sink_s in items and items[self.hunter_sink_s] == zmq.POLLIN:
                self.handle_message(self.hunter_sink_s)

    def handle_message(self, s):
        self.logger.debug('message received')

        m = s.recv_multipart()

        self.logger.debug(m)

        try:
            id, null, token, mtype, data = m
        except ValueError:
            id, token, mtype, data = m

        mtype = mtype.decode('utf-8')

        self.logger.debug("mtype: {0}".format(mtype))

        if mtype in ['indicators_create', 'indicators_search']:
            handler = getattr(self, "handle_" + mtype)
        else:
            handler = self.handle_message_default

        try:
            handler(id, mtype, token, data)
        except Exception as e:
            self.logger.error(e)
            traceback.print_exc()

        self.logger.debug('handler: {}'.format(handler))
        self.count += 1
        if (self.count % 100) == 0:
            t = (time.time() - self.count_start)
            n = self.count / t
            self.logger.info('processing {} msgs per {} sec'.format(round(n, 2), round(t, 2)))
            self.count = 0
            self.count_start = time.time()

    def handle_message_default(self, id, mtype, token, data='[]'):
        self.logger.debug('sending message to store...')
        self.store_s.send_multipart([id, ''.encode('utf-8'), mtype.encode('utf-8'), token, data])

    def handle_message_store(self, s):
        self.logger.debug('msg from store received')
        m = s.recv_multipart()
        self.logger.debug(m)

        id, null, mtype, rv = m

        self.frontend_s.send_multipart([id, null, mtype, rv])

    def handle_message_gatherer(self, s):
        self.logger.debug('received message from gatherer')
        m = s.recv_multipart()

        self.logger.debug(m)

        id, null, mtype, token, data = m

        data = json.loads(data)
        if isinstance(data, dict):
            data = [data]

        self.logger.debug('sending to hunters...')
        for d in data:
            self.logger.debug(d)
            i = Indicator(**d)

            d = json.dumps(d)

            if i.confidence >= HUNTER_MIN_CONFIDENCE:
                if self.p2p:
                    self.logger.info('sending to peers...')
                    self.p2p.send(data.encode('utf-8'))

                if self.hunters_s:
                    self.hunters_s.send_string(d)

        self.logger.debug('sending to store')
        data = json.dumps(data)
        self.store_s.send_multipart([id, b'', b'indicators_create', token, data.encode('utf-8')])
        self.logger.debug('done')

    def handle_indicators_search(self, id, mtype, token, data):
        self.store_s.send_multipart([id, b'', mtype.encode('utf-8'), token, data])
        data = json.loads(data)

        if data.get('indicator'):
            data = Indicator(
                indicator=data['indicator'],
                tlp='green',
                confidence=10,
                tags=['search'],
            )
            data = str(data).encode('utf-8')
            self.gatherer_s.send_multipart([id, b'', b'indicators_create', token, data])

    def handle_indicators_create(self, id, mtype, token, data):
        self.logger.debug('sending to gatherers..')
        data = json.loads(data)
        if isinstance(data, dict):
            data = [data]

        data = json.dumps(data).encode('utf-8')
        self.gatherer_s.send_multipart([id, ''.encode('utf-8'), mtype.encode('utf-8'), token, data])


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

    p.add_argument('--p2p', action='store_true', help='enable experimental p2p support')

    p.add_argument('--logging-ignore', help='set logging to WARNING for specific modules')

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

    setup_signals(__name__)

    setup_runtime_path(args.runtime_path)

    with Router(listen=args.listen, hunter=args.hunter, store_type=args.store, store_address=args.store_address,
                store_nodes=args.store_nodes, p2p=args.p2p, hunter_token=args.hunter_token, hunter_threads=args.hunter_threads,
                gatherer_threads=args.gatherer_threads) as r:
        try:
            logger.info('starting router..')
            r.start()
        except KeyboardInterrupt:
            # todo - signal to threads to shut down and wait for them to finish
            logger.info('shutting down...')

    logger.info('Shutting down')

if __name__ == "__main__":
    main()
