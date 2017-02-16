#!/usr/bin/env python

import ujson as json
import logging
import traceback
import zmq
import multiprocessing
from cifsdk.msg import Msg
import os
import cif.gatherer
from cif.constants import GATHERER_ADDR, GATHERER_SINK_ADDR
from csirtg_indicator import Indicator

SNDTIMEO = 15000
LINGER = 0

logger = logging.getLogger(__name__)
TRACE = os.environ.get('CIF_ROUTER_TRACE') or os.environ.get('CIF_GATHERER_TRACE')

logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)

if TRACE:
    logger.setLevel(logging.DEBUG)


class Gatherer(multiprocessing.Process):
    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        return self

    def __init__(self, pull=GATHERER_ADDR, push=GATHERER_SINK_ADDR):
        multiprocessing.Process.__init__(self)
        self.pull = pull
        self.push = push
        self.exit = multiprocessing.Event()

    def _init_plugins(self):
        import pkgutil
        self.gatherers = []
        logger.debug('loading plugins...')
        for loader, modname, is_pkg in pkgutil.iter_modules(cif.gatherer.__path__, 'cif.gatherer.'):
            p = loader.find_module(modname).load_module(modname)
            self.gatherers.append(p.Plugin())
            logger.debug('plugin loaded: {}'.format(modname))

    def terminate(self):
        self.exit.set()

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

        poller = zmq.Poller()
        poller.register(pull_s)

        while not self.exit.is_set():
            try:
                s = dict(poller.poll(1000))
            except Exception as e:
                self.logger.error(e)
                break

            if pull_s in s:
                id, token, mtype, data = Msg().recv(pull_s)

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
                            from pprint import pprint
                            pprint(i)

                            logger.error('gatherer failed: %s' % g)
                            logger.error(e)
                            traceback.print_exc()

                    rv.append(i.__dict__())

                data = json.dumps(rv)
                logger.debug('sending back to router...')
                Msg(id=id, mtype=mtype, token=token, data=data).send(push_s)

        logger.info('shutting down gatherer..')