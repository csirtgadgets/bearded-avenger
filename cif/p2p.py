from pyre import Pyre
from pyre import zhelper
import zmq
import uuid
import logging
import json
import sys

from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter
import textwrap

LOG_FORMAT = '%(asctime)s - %(levelname)s - %(name)s[%(lineno)s] - %(message)s'

ZYRE_CHANNEL = 'CIF'


class Client(object):

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.engine.stop()

    def __init__(self, channel=ZYRE_CHANNEL, *args, **kvargs):

        self.logger = logging.getLogger('pyre')
        self.channel = channel
        self.engine = Pyre(self.channel)
        self.id = self.engine.uuid()

    def start(self, ctx, pipe):
        self.logger.info('joining channel')
        self.engine.join(self.channel)

        self.logger.info('starting engine...')
        self.engine.start()

        self.logger.info('id is: {}'.format(self.id))

        poller = zmq.Poller()
        poller.register(pipe, zmq.POLLIN)
        poller.register(self.engine.socket(), zmq.POLLIN)

        while True:
            items = dict(poller.poll())
            if pipe in items and items[pipe] == zmq.POLLIN:
                message = pipe.recv()

                # message to quit
                if message.decode('utf-8') == "$$STOP":
                    break

                self.logger.info("CHAT_TASK: %s" % message)
                self.engine.shouts(self.channel, message.decode('utf-8'))
            else:
                cmds = self.engine.recv()
                self.logger.info('HMMM {}'.format(cmds))

                msg_type = cmds.pop(0)
                self.logger.info("NODE_MSG TYPE: %s" % msg_type)
                self.logger.info("NODE_MSG PEER: %s" % uuid.UUID(bytes=cmds.pop(0)))
                self.logger.info("NODE_MSG NAME: %s" % cmds.pop(0))

                if msg_type.decode('utf-8') == "SHOUT":
                    self.logger.info("NODE_MSG GROUP: %s" % cmds.pop(0))
                elif msg_type.decode('utf-8') == "ENTER":
                    headers = json.loads(cmds.pop(0).decode('utf-8'))
                    self.logger.info("NODE_MSG HEADERS: %s" % headers)

                    for key in headers:
                        self.logger.info("key = {0}, value = {1}".format(key, headers[key]))

                self.logger.info("NODE_MSG CONT: %s" % cmds)

        self.engine.stop()

def main():
    p = ArgumentParser(
        description=textwrap.dedent('''\
        To test, run two separate instances of chat.py on the same LAN and type into the console when they are running

        example usage:
            $ python tapio.py -h
            $ python tapio.py -d
        '''),
        formatter_class=RawDescriptionHelpFormatter
    )

    p.add_argument('-d', '--debug', dest='debug', action="store_true")
    args = p.parse_args()

    # Create a StreamHandler for debugging
    logger = logging.getLogger("pyre")
    logger.setLevel(logging.INFO)
    if args.debug:
        logger.setLevel(logging.DEBUG)

    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter(LOG_FORMAT))
    logger.addHandler(console)
    logger.propagate = False

    ctx = zmq.Context()
    client = Client()
    chat_pipe = zhelper.zthread_fork(ctx, client.start)

    logger.info('starting loop')
    stop = False
    while not stop:
        try:
            if sys.version_info.major < 3:
                msg = raw_input('message to send: ')
            else:
                msg = input()

            chat_pipe.send(msg.encode('utf_8'))
        except (KeyboardInterrupt, SystemExit):
            logger.info('SIGINT Received')
            stop = True
        except AttributeError as e:
            stop = True
            logger.error(e)
        else:
            stop = True

    chat_pipe.send("$$STOP".encode('utf_8'))
    logger.info("FINISHED")

if __name__ == '__main__':
    main()