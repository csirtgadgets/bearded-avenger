#!/usr/bin/env python

import ujson as json
import logging
import traceback
import zmq

import cif.gatherer
from cif.constants import GATHERER_ADDR, GATHERER_SINK_ADDR
from csirtg_indicator import Indicator

logger = logging.getLogger(__name__)

SNDTIMEO = 15000
LINGER = 0


class Gatherer(object):
    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        return self

    def __init__(self, pull=GATHERER_ADDR, push=GATHERER_SINK_ADDR):

        self.pull = pull
        self.push = push

    def _init_plugins(self):
        import pkgutil
        self.gatherers = []
        logger.debug('loading plugins...')
        for loader, modname, is_pkg in pkgutil.iter_modules(cif.gatherer.__path__, 'cif.gatherer.'):
            p = loader.find_module(modname).load_module(modname)
            self.gatherers.append(p.Plugin())
            logger.debug('plugin loaded: {}'.format(modname))

    def start(self):
        self._init_plugins()

        context = zmq.Context()
        pull_s = context.socket(zmq.PULL)
        push_s = context.socket(zmq.PUSH)

        push_s.SNDTIMEO = SNDTIMEO

        logger.debug('connecting to sockets...')
        pull_s.connect(self.pull)
        push_s.connect(self.push)
        logger.debug('starting Gatherer')

        try:
            while True:
                m = pull_s.recv_multipart()

                logger.debug(m)

                id, null, mtype, token, data = m

                data = json.loads(data)
                if isinstance(data, dict):
                    data = [data]

                rv = []
                for d in data:
                    i = Indicator(**d)

                    for g in self.gatherers:
                        try:
                            g.process(i)
                        except Exception as e:
                            logger.error('gatherer failed: %s' % g)
                            logger.error(e)
                            traceback.print_exc()

                    rv.append(i.__dict__())

                data = json.dumps(rv)
                logger.debug('sending back to router...')
                push_s.send_multipart([id, null, mtype, token, data.encode('utf-8')])

        except KeyboardInterrupt:
            logger.info('shutting down gatherer..')
            return
