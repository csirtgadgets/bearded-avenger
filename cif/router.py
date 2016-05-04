#!/usr/bin/env python

import json
import logging
import textwrap
import time
from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter

import zmq
from zmq.eventloop import ioloop

from cif.constants import CTRL_ADDR, ROUTER_ADDR, STORAGE_ADDR, HUNTER_ADDR
from cif.utils import setup_logging, get_argument_parser, setup_signals
import cif.gatherer
from cif.indicator import Indicator
from cif.utils import zhelper

from pprint import pprint

MIN_CONFIDENCE = 3


class Router(object):

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.stop()
        if self.p2p:
            self.p2p.send("$$STOP".encode('utf_8'))

    def __init__(self, listen=ROUTER_ADDR, hunter=HUNTER_ADDR, storage=STORAGE_ADDR, p2p=False):
        self.logger = logging.getLogger(__name__)

        self.context = zmq.Context.instance()
        self.frontend = self.context.socket(zmq.ROUTER)
        self.hunters = self.context.socket(zmq.PUB)
        self.storage = self.context.socket(zmq.DEALER)
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
        self.storage.bind(storage)
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

    def handle_message(self, s, e):
        self.logger.debug('message received')
        m = s.recv_multipart()

        id, null, token, mtype, data = m
        self.logger.debug("mtype: {0}".format(mtype))

        handler = getattr(self, "handle_" + mtype)
        self.logger.debug('handler: {}'.format(handler))
        rv = handler(token, data)

        self.logger.debug("replying {}".format(rv))
        self.frontend.send_multipart([id, '', mtype, rv])

    def handle_ping(self, token, data):
        self.logger.info('sending to hunters..')
        rv = {
            "status": "success",
            "data": str(time.time())
        }
        return json.dumps(rv)

    def handle_write(self, data):
        rv = {
            "status": "failed",
            "data": str(time.time())
        }
        return json.dumps(rv)

    def handle_search(self, token, data):
        # need to send searches through the _submission pipe
        data = json.loads(data)
        if data.get('indicator'):
            i = Indicator(
                indicator=data['indicator'],
                tlp='green',
                confidence=5,
                tags='search'
            )
            r = self.handle_submission(token, str(i))
            if r:
                self.logger.info('search logged')

        data = json.dumps(data)
        self.storage.send_multipart(['search', token, data])
        return self.storage.recv()

    def handle_submission(self, token, data):
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

        if i.confidence >= MIN_CONFIDENCE:
            if self.p2p:
                self.logger.info('sending to peers...')
                self.p2p.send(data.encode('utf-8'))

            self.hunters.send(data)

        self.storage.send_multipart(['submission', token, data])
        m = self.storage.recv()
        return m

    def handle_tokens_create(self, token, data):
        self.storage.send_multipart(['tokens_create', token, data])
        return self.storage.recv()

    def handle_tokens_delete(self, token, data):
        self.storage.send_multipart(['tokens_delete', token, data])
        return self.storage.recv()

    def handle_tokens_search(self, token, data):
        self.storage.send_multipart(['tokens_search', token, data])
        return self.storage.recv()

    def run(self):
        self.logger.debug('starting loop')
        loop = ioloop.IOLoop.instance()
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
            CIF_STORAGE_ADDR

        example usage:
            $ cif-router --listen 0.0.0.0 -d
        '''),
        formatter_class=RawDescriptionHelpFormatter,
        prog='cif-router',
        parents=[p]
    )

    p.add_argument('--listen', help='address to listen on [default: %(default)s]', default=ROUTER_ADDR)
    p.add_argument('--hunter', help='address hunters listen on on [default: %(default)s]', default=HUNTER_ADDR)
    p.add_argument("--storage", help="specify a storage address [default: %(default)s]",
                   default=STORAGE_ADDR)

    p.add_argument('--p2p', action='store_true', help='enable experimental p2p support')

    args = p.parse_args()
    setup_logging(args)
    logger = logging.getLogger(__name__)
    logger.info('loglevel is: {}'.format(logging.getLevelName(logger.getEffectiveLevel())))

    setup_signals(__name__)

    with Router(listen=args.listen, hunter=args.hunter, storage=args.storage, p2p=args.p2p) as r:
        try:
            logger.info('starting router..')
            r.run()
        except KeyboardInterrupt:
            logger.info('shutting down...')

    logger.info('Shutting down')

if __name__ == "__main__":
    main()
