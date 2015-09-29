import logging
import zmq

from zmq.eventloop import ioloop


class Generic(object):
    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        return self

    def __init__(self, context=zmq.Context.instance(), socket=zmq.ROUTER):
        self.logger = logging.getLogger(__name__)
        self.context = context
        self.socket = self.context.socket(socket)
        self.poller = zmq.Poller()

    def handle_message(self, s, e):
        pass

    def run(self):
        self.logger.debug('starting loop')
        loop = ioloop.IOLoop.instance()
        loop.add_handler(self.socket, self.handle_message, zmq.POLLIN)
        loop.start()