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
from cif.utils import strtobool
from csirtg_indicator import Indicator, InvalidIndicator
import time

SNDTIMEO = 30000
LINGER = 0

logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)

TRACE = strtobool(os.environ.get('CIF_GATHERER_TRACE', False))
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
                logger.error(e)
                break

            if pull_s in s:
                id, token, mtype, data = Msg().recv(pull_s)

                try:
                    data = json.loads(data)
                except Exception as e:
                    logger.error('malformed data send to gatherer: {}'.format(e))
                    break

                if isinstance(data, dict):
                    data = [data]

                rv = []
                start = time.time()
                for d in data:
                    try:
                        i = Indicator(**d)

                    except InvalidIndicator as e:
                        logger.error('resolving failed for indicator: {}'.format(d))
                        logger.error(e)
                        traceback.print_exc()
                        # skip failed indicator
                        continue

                    for g in self.gatherers:
                        try:
                            g.process(i)
                        except Exception as e:
                            logger.error('gatherer failed on indicator {}: {}'.format(i, g))
                            logger.error(e)
                            traceback.print_exc()

                    rv.append(i.__dict__())

                data = json.dumps(rv)
                logger.debug('sending back to router: %f' % (time.time() - start))
                Msg(id=id, mtype=mtype, token=token, data=data).send(push_s)

        logger.info('shutting down gatherer..')
