#!/usr/bin/env python

import ujson as json
import logging
import zmq
import cif.hunter
from cifsdk.msg import Msg
from cifsdk.client.zeromq import ZMQ as Client
from cif.constants import HUNTER_ADDR, HUNTER_SINK_ADDR
from csirtg_indicator import Indicator
from csirtg_indicator.exceptions import InvalidIndicator
import multiprocessing
import os
from cif.utils import strtobool


SNDTIMEO = 15000
ZMQ_HWM = 1000000
EXCLUDE = os.environ.get('CIF_HUNTER_EXCLUDE', None)
HUNTER_ADVANCED = os.getenv('CIF_HUNTER_ADVANCED', 0)
HUNTER_MIN_CONFIDENCE = 4

HUNTER_RECURSION = strtobool(os.getenv('CIF_HUNTER_RECURSION', False))

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

TRACE = strtobool(os.environ.get('CIF_HUNTER_TRACE', False))
if TRACE:
   logger.setLevel(logging.DEBUG)


class Hunter(multiprocessing.Process):
    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        return self

    def __init__(self, remote=HUNTER_ADDR, token=None):
        multiprocessing.Process.__init__(self)
        self.hunters = remote
        self.router = HUNTER_SINK_ADDR
        self.token = token
        self.exit = multiprocessing.Event()
        self.exclude = {}

        logger.debug('setting hunter recursion to: {}'.format(HUNTER_RECURSION))

        if EXCLUDE:
            for e in EXCLUDE.split(','):
                provider, tag = e.split(':')

                if not self.exclude.get(provider):
                    self.exclude[provider] = set()

                logger.debug('setting hunter to skip: {}/{}'.format(provider, tag))
                self.exclude[provider].add(tag)

    def _load_plugins(self):
        import pkgutil
        logger.debug('loading plugins...')
        plugins = []
        for loader, modname, is_pkg in pkgutil.iter_modules(cif.hunter.__path__, 'cif.hunter.'):
            p = loader.find_module(modname).load_module(modname)
            plugins.append(p.Plugin())
            logger.debug('plugin loaded: {}'.format(modname))

        return plugins

    def terminate(self):
        self.exit.set()

    def start(self):
        router = Client(remote=self.router, token=self.token, nowait=True, autoclose=False)
        plugins = self._load_plugins()
        socket = zmq.Context().socket(zmq.PULL)

        socket.SNDTIMEO = SNDTIMEO
        socket.set_hwm(ZMQ_HWM)

        logger.debug('connecting to {}'.format(self.hunters))
        socket.connect(self.hunters)
        logger.debug('starting hunter')

        poller = zmq.Poller()
        poller.register(socket, zmq.POLLIN)

        while not self.exit.is_set():
            try:
                s = dict(poller.poll(1000))
            except SystemExit or KeyboardInterrupt:
                break

            if socket not in s:
                continue

            id, token, mtype, data = Msg().recv(socket)

            data = json.loads(data)

            if isinstance(data, dict):
                if not data.get('indicator'):
                    continue

                if not data.get('itype'):
                    nolog = data.get('nolog', False)
                    try:
                        data = Indicator(
                            indicator=data['indicator'],
                            tags='search',
                            confidence=10,
                            group='everyone',
                            tlp='amber',
                        ).__dict__()
                        data['nolog'] = nolog
                    except InvalidIndicator:
                        logger.debug('skipping invalid indicator: {}'.format(data['indicator']))
                        continue

                if not data.get('tags'):
                    data['tags'] = []

                data = [data]

            token = json.loads(token)

            for d in data:
                try:
                    nolog = strtobool(d.get('nolog', False))
                except ValueError:
                    nolog = False
                try:
                    d = Indicator(**d)
                except Exception as e:
                    logger.error('hunter pipeline received indicator "{}" that produced error: {}'.format(d, e))
                    continue

                if d.confidence < HUNTER_MIN_CONFIDENCE:
                    continue

                # prevent hunter recursion if disabled
                if not HUNTER_RECURSION and d.tags and 'hunter' in d.tags:
                    continue

                if d.indicator in ["", 'localhost', 'example.com']:
                    continue

                if self.exclude.get(d.provider):
                    for t in d.tags:
                        if t in self.exclude[d.provider]:
                            logger.debug('skipping: {}'.format(d.indicator))
                            continue

                for p in plugins:
                    if not HUNTER_ADVANCED and p.is_advanced:
                        continue
                    try:
                        p.process(i=d, router=router, user_token=token, mtype=mtype, nolog=nolog)
                    except Exception as e:
                        logger.error(e)
                        logger.error('[{}] giving up on: {}'.format(p, d))
