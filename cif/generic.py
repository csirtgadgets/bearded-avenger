#!/usr/bin/env python

import logging
import zmq
import sys
from pprint import pprint

from zmq.eventloop import ioloop


class Generic(object):

    def __init__(self, logger=logging.getLogger(__name__), context=zmq.Context.instance(), socket=zmq.ROUTER):
        self.logger = logger
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



def main():
    g = Generic()
    g.run()

if __name__ == "__main__":
    main()