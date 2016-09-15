#!/usr/bin/env python

import ujson as json
import logging
import traceback
import zmq

import cif.gatherer
from cif.constants import GATHERER_ADDR, GATHERER_SINK_ADDR
from csirtg_indicator import Indicator


class Gatherer(object):

    def __init__(self, context, pull=GATHERER_ADDR, push=GATHERER_SINK_ADDR):

        self.logger = logging.getLogger(__name__)
        self.context = context

        self.pull = pull
        self.push = push

        self.pull_s = self.context.socket(zmq.PULL)
        self.push_s = self.context.socket(zmq.PUSH)

        self._init_plugins()

    def _init_plugins(self):
        import pkgutil
        self.gatherers = []
        self.logger.debug('loading plugins...')
        for loader, modname, is_pkg in pkgutil.iter_modules(cif.gatherer.__path__, 'cif.gatherer.'):
            p = loader.find_module(modname).load_module(modname)
            self.gatherers.append(p.Plugin())
            self.logger.debug('plugin loaded: {}'.format(modname))

    def start(self):
        self.logger.debug('connecting to sockets...')
        self.pull_s.connect(self.pull)
        self.push_s.connect(self.push)
        self.logger.debug('starting Gatherer')

        while True:
            m = self.pull_s.recv_multipart()
            self.logger.debug(m)

            id, null, mtype, token, data = m

            data = json.loads(data)
            i = Indicator(**data)

            for g in self.gatherers:
                try:
                    g.process(i)
                except Exception as e:
                    self.logger.error('gatherer failed: %s' % g)
                    self.logger.error(e)
                    traceback.print_exc()

            data = str(i)

            self.logger.debug('sending back to router...')
            self.push_s.send_multipart([id, null, mtype, token, data.encode('utf-8')])
