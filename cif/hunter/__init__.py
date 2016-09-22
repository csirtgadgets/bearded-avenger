#!/usr/bin/env python

import ujson as json
import logging
import traceback
import zmq
from pprint import pprint

import cif.hunter
from cifsdk.client.zeromq import ZMQ as Client
from cif.constants import HUNTER_ADDR, ROUTER_ADDR, HUNTER_SINK_ADDR
from csirtg_indicator import Indicator

logger = logging.getLogger(__name__)

SNDTIMEO = 15000
ZMQ_HWM = 1000000


class Hunter(object):
    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        return self

    def __init__(self, remote=HUNTER_ADDR, router=ROUTER_ADDR, token=None):
        self.hunters = remote
        self.router = HUNTER_SINK_ADDR
        self.token = token

    def _load_plugins(self):
        import pkgutil
        logger.debug('loading plugins...')
        plugins = []
        for loader, modname, is_pkg in pkgutil.iter_modules(cif.hunter.__path__, 'cif.hunter.'):
            p = loader.find_module(modname).load_module(modname)
            plugins.append(p.Plugin())
            logger.debug('plugin loaded: {}'.format(modname))

        return plugins

    def start(self):
        # TODO - convert this to an async socket
        router = Client(remote=self.router, token=self.token, nowait=True)
        plugins = self._load_plugins()
        socket = zmq.Context().socket(zmq.PULL)

        socket.SNDTIMEO = SNDTIMEO
        socket.set_hwm(ZMQ_HWM)

        logger.debug('connecting to {}'.format(self.hunters))
        socket.connect(self.hunters)
        logger.debug('starting hunter')

        try:
            while True:
                logger.debug('waiting...')
                data = socket.recv()
                logger.debug(data)

                data = json.loads(data)
                if isinstance(data, dict):
                    data = [data]

                for d in data:
                    d = Indicator(**d)

                    for p in plugins:
                        try:
                            p.process(d, router)
                        except Exception as e:
                            logger.error(e)
                            traceback.print_exc()
                            logger.error('giving up on: {}'.format(d))
        except KeyboardInterrupt:
            logger.info('shutting down hunter...')
            return
