#!/usr/bin/env python

import ujson as json
import logging
import traceback
import zmq
from pprint import pprint

import cif.hunter
from cifsdk.client.zeromq import ZMQ as Client
from cif.constants import HUNTER_ADDR, ROUTER_ADDR
from csirtg_indicator import Indicator


class Hunter(object):

    def __init__(self, context, remote=HUNTER_ADDR, router=ROUTER_ADDR, token=None):

        self.logger = logging.getLogger(__name__)
        self.context = context
        self.socket = self.context.socket(zmq.PULL)

        self.plugins = self._load_plugins()
        self.hunters = remote

        # TODO - convert this to an async socket
        self.router = Client(remote=router, token=token)

    def _load_plugins(self):
        import pkgutil
        self.logger.debug('loading plugins...')
        plugins = []
        for loader, modname, is_pkg in pkgutil.iter_modules(cif.hunter.__path__, 'cif.hunter.'):
            p = loader.find_module(modname).load_module(modname)
            plugins.append(p.Plugin())
            self.logger.debug('plugin loaded: {}'.format(modname))

        return plugins

    def start(self):
        self.logger.debug('connecting to {}'.format(self.hunters))
        self.socket.connect(self.hunters)
        self.logger.debug('starting hunter')

        while True:
            m = self.socket.recv()
            self.logger.debug(m)

            m = json.loads(m)

            m = Indicator(**m)

            for p in self.plugins:
                try:
                    p.process(m, self.router)
                except Exception as e:
                    self.logger.error(e)
                    traceback.print_exc()
                    self.logger.error('giving up on: {}'.format(m))

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        return self
