#!/usr/bin/env python

import ujson as json
import logging
import textwrap
import traceback
from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter
from pprint import pprint
from time import sleep

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
from cifsdk.msg import Msg

HUNTER_MIN_CONFIDENCE = 2
HUNTER_THREADS = os.getenv('CIF_HUNTER_THREADS', 2)
GATHERER_THREADS = os.getenv('CIF_GATHERER_THREADS', 2)
STORE_DEFAULT = 'sqlite'
STORE_PLUGINS = ['cif.store.dummy', 'cif.store.sqlite', 'cif.store.elasticsearch', 'cif.store.rdflib']

ZMQ_HWM = 1000000
ZMQ_SNDTIMEO = 5000
ZMQ_RCVTIMEO = 5000
FRONTEND_TIMEOUT = os.environ.get('CIF_FRONTEND_TIMEOUT', 100)

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
                 store_nodes=None, hunter_token=HUNTER_TOKEN, hunter_threads=HUNTER_THREADS,
                 gatherer_threads=GATHERER_THREADS, test=False):

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

        self.hunter_sink_s = self.context.socket(zmq.ROUTER)
        self.hunter_sink_s.bind(HUNTER_SINK_ADDR)

        self.hunters = []
        if int(hunter_threads):
            self.hunters_s = self.context.socket(zmq.PUSH)
            self.logger.debug('binding hunter: {}'.format(hunter))
            self.hunters_s.bind(hunter)

            self._init_hunters(hunter_threads, hunter_token)
        else:
            self.hunters_s = None

        self.logger.info('launching frontend...')
        self.frontend_s = self.context.socket(zmq.ROUTER)
        self.frontend_s.set_hwm(ZMQ_HWM)
        self.frontend_s.bind(listen)

        self.count = 0
        self.count_start = time.time()

        self.poller = zmq.Poller()

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

    def stop(self):
        self.terminate = True
        self.logger.info('stopping hunters..')
        for h in self.hunters:
            h.terminate()

        self.logger.info('stopping gatherers')
        for g in self.gatherers:
            g.terminate()

        self.logger.info('stopping store..')
        self.store_p.terminate()

        sleep(0.01)

    def start(self):
        self.logger.debug('starting loop')

        self.poller.register(self.hunter_sink_s, zmq.POLLIN)
        self.poller.register(self.gatherer_sink_s, zmq.POLLIN)
        self.poller.register(self.store_s, zmq.POLLIN)
        self.poller.register(self.frontend_s, zmq.POLLIN)

        # we use this instead of a loop so we can make sure to get front end queries as they come in
        # that way hunters don't over burden the store, think of it like QoS
        # it's weighted so front end has a higher chance of getting a faster response
        while not self.terminate:
            items = dict(self.poller.poll(FRONTEND_TIMEOUT))

            if self.frontend_s in items and items[self.frontend_s] == zmq.POLLIN:
                self.handle_message(self.frontend_s)

            if self.store_s in items and items[self.store_s] == zmq.POLLIN:
                self.handle_message_store(self.store_s)

            if self.gatherer_sink_s in items and items[self.gatherer_sink_s] == zmq.POLLIN:
                self.handle_message_gatherer(self.gatherer_sink_s)

            if self.hunter_sink_s in items and items[self.hunter_sink_s] == zmq.POLLIN:
                self.handle_message(self.hunter_sink_s)

    def _log_counter(self):
        self.count += 1
        if (self.count % 100) == 0:
            t = (time.time() - self.count_start)
            n = self.count / t
            self.logger.info('processing {} msgs per {} sec'.format(round(n, 2), round(t, 2)))
            self.count = 0
            self.count_start = time.time()

    def handle_message(self, s):
        id, token, mtype, data = Msg().recv(s)

        if mtype in ['indicators_create', 'indicators_search']:
            handler = getattr(self, "handle_" + mtype)
        else:
            handler = self.handle_message_default

        try:
            handler(id, mtype, token, data)
        except Exception as e:
            self.logger.error(e)
            traceback.print_exc()

        self._log_counter()

    def handle_message_default(self, id, mtype, token, data='[]'):
        self.logger.debug('sending message to store...')
        Msg(id=id, mtype=mtype, token=token, data=data).send(self.store_s)

    def handle_message_store(self, s):
        self.logger.debug('msg from store received')

        # re-routing from store to front end
        id, mtype, token, data = Msg().recv(s)
        Msg(id=id, mtype=mtype, token=token, data=data).send(self.frontend_s)

    def handle_message_gatherer(self, s):
        self.logger.debug('received message from gatherer')
        id, token, mtype, data = Msg().recv(s)

        self.logger.debug('sending to store')
        Msg(id=id, mtype=mtype, token=token, data=data).send(self.store_s)

        if len(self.hunters) > 0:
            self.logger.debug('sending to hunters...')
            data = json.loads(data)
            if isinstance(data, dict):
                data = [data]

            for d in data:
                if d.get('confidence', 0) >= HUNTER_MIN_CONFIDENCE:
                    self.hunters_s.send_string(json.dumps(d))

    def handle_indicators_search(self, id, mtype, token, data):
        self.handle_message_default(id, mtype, token, data)
        self.logger.debug('sending to hunters..')
        self.hunters_s.send_string(data)

    def handle_indicators_create(self, id, mtype, token, data):
        self.logger.debug('sending to gatherers..')
        Msg(id=id, mtype=mtype, token=token, data=data).send(self.gatherer_s)


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

if __name__ == "__main__":
    main()
