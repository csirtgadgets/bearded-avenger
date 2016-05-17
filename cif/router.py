#!/usr/bin/env python

import json
import logging
import textwrap
import time
import traceback
from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter

import zmq
from zmq.eventloop import ioloop

import cif.gatherer
from cif.constants import CTRL_ADDR, ROUTER_ADDR, STORE_ADDR, HUNTER_ADDR
from cifsdk.utils import setup_logging, get_argument_parser, setup_signals, zhelper
from csirtg_indicator import Indicator

HUNTER_MIN_CONFIDENCE = 3


class Router(object):

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.stop()
        if self.p2p:
            self.p2p.send("$$STOP".encode('utf_8'))

    def __init__(self, listen=ROUTER_ADDR, hunter=HUNTER_ADDR, store=STORE_ADDR, p2p=False):
        self.logger = logging.getLogger(__name__)

        self.context = zmq.Context.instance()
        self.frontend = self.context.socket(zmq.ROUTER)
        self.hunters = self.context.socket(zmq.PUB)
        self.store = self.context.socket(zmq.DEALER)
        self.ctrl = self.context.socket(zmq.REP)
        self.p2p = p2p

        if self.p2p:
            self._init_p2p()

        self.poller = zmq.Poller()

        try:
            self.ctrl.bind(CTRL_ADDR)
        except zmq.error.ZMQError as e:
            self.logger.error('unable to bind to: {}'.format(CTRL_ADDR))
            self.logger.error(e)
            raise SystemExit

        self._init_gatherers()
        self.store.bind(store)
        self.hunters.bind(hunter)
        self.frontend.bind(listen)

    def _init_p2p(self):
        self.logger.info('enabling p2p..')
        from cif.p2p import Client as p2pcli
        self.p2p = p2pcli(channel='CIF')
        p2p_pipe = zhelper.zthread_fork(self.context, self.p2p.start)
        self.p2p = p2p_pipe

    def _init_gatherers(self):
        import pkgutil
        self.gatherers = []
        self.logger.debug('loading plugins...')
        for loader, modname, is_pkg in pkgutil.iter_modules(cif.gatherer.__path__, 'cif.gatherer.'):
            p = loader.find_module(modname).load_module(modname)
            self.gatherers.append(p.Plugin())
            self.logger.debug('plugin loaded: {}'.format(modname))

    def handle_ctrl(self, s, e):
        """

        :rtype: object
        """
        self.logger.debug('ctrl msg recieved')
        id, mtype, data = s.recv_multipart()

        self.ctrl.send_multipart(['router', 'ack', str(time.time())])

    def handle_store_default(self, mtype, token, data='[]'):
        self.store.send_multipart([mtype, token, data])
        return self.store.recv()

    def handle_message(self, s, e):
        self.logger.debug('message received')
        m = s.recv_multipart()

        self.logger.debug(m)

        id, null, token, mtype, data = m
        self.logger.debug("mtype: {0}".format(mtype))

        rv = json.dumps({'status': 'failed'})

        if mtype in ['indicators_search', 'indicators_create', 'token_write']:
            handler = getattr(self, "handle_" + mtype)
            try:
                rv = handler(token, data)
            except Exception as e:
                self.logger.error(e)
                traceback.print_exc()
        else:
            handler = self.handle_store_default
            try:
                rv = handler(mtype, token, data)
            except Exception as e:
                self.logger.error(e)
                traceback.print_exc()

        self.logger.debug('handler: {}'.format(handler))

        self.logger.debug("replying {}".format(rv))
        self.frontend.send_multipart([id, '', mtype, rv])

    def handle_ping_write(self, token, data='[]'):
        self.store.send_multipart(['token_write', token, data])
        return self.store.recv()

    def handle_indicators_search(self, token, data):
        # need to send searches through the _submission pipe
        self.store.send_multipart(['indicators_search', token, data])
        x = self.store.recv()

        data = json.loads(data)
        if data.get('indicator'):
            i = Indicator(
                indicator=data['indicator'],
                tlp='green',
                confidence=10,
                tags='search'
            )
            r = self.handle_indicators_create(token, str(i))
            if r:
                self.logger.info('search logged')

        return x

    def handle_indicators_create(self, token, data):
        # this needs to be threaded out, badly.
        data = json.loads(data)
        i = Indicator(**data)
        for g in self.gatherers:
            try:
                i = g.process(i)
            except Exception as e:
                self.logger.error('gatherer failed: %s' % g)
                self.logger.error(e)

        data = str(i)

        if i.confidence >= HUNTER_MIN_CONFIDENCE:
            if self.p2p:
                self.logger.info('sending to peers...')
                self.p2p.send(data.encode('utf-8'))

            self.hunters.send(data)

        self.store.send_multipart(['indicators_create', token, data])
        m = self.store.recv()
        return m

    def run(self, loop=ioloop.IOLoop.instance()):
        self.logger.debug('starting loop')
        loop.add_handler(self.frontend, self.handle_message, zmq.POLLIN)
        loop.add_handler(self.ctrl, self.handle_ctrl, zmq.POLLIN)
        loop.start()

    def stop(self):
        return self


def main():
    p = get_argument_parser()
    p = ArgumentParser(
        description=textwrap.dedent('''\
        Env Variables:
            CIF_RUNTIME_PATH
            CIF_ROUTER_ADDR
            CIF_HUNTER_ADDR
            CIF_STORE_ADDR

        example usage:
            $ cif-router --listen 0.0.0.0 -d
        '''),
        formatter_class=RawDescriptionHelpFormatter,
        prog='cif-router',
        parents=[p]
    )

    p.add_argument('--listen', help='address to listen on [default: %(default)s]', default=ROUTER_ADDR)
    p.add_argument('--hunter', help='address hunters listen on on [default: %(default)s]', default=HUNTER_ADDR)
    p.add_argument("--store", help="specify a store address [default: %(default)s]",
                   default=STORE_ADDR)

    p.add_argument('--p2p', action='store_true', help='enable experimental p2p support')

    args = p.parse_args()
    setup_logging(args)
    logger = logging.getLogger(__name__)
    logger.info('loglevel is: {}'.format(logging.getLevelName(logger.getEffectiveLevel())))

    setup_signals(__name__)

    with Router(listen=args.listen, hunter=args.hunter, store=args.store, p2p=args.p2p) as r:
        try:
            logger.info('starting router..')
            r.run()
        except KeyboardInterrupt:
            logger.info('shutting down...')

    logger.info('Shutting down')

if __name__ == "__main__":
    main()
