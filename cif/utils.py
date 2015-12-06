import pkgutil
import logging
from cif.constants import LOG_FORMAT, RUNTIME_PATH, LOGLEVEL
from argparse import ArgumentParser
import signal
import cif.color


def get_argument_parser():
    BasicArgs = ArgumentParser(add_help=False)
    BasicArgs.add_argument('-d', '--debug', dest='debug', action="store_true")
    BasicArgs.add_argument(
        "--runtime-directory", help="specify the runtime path [default %(default)s]", default=RUNTIME_PATH
    )
    return ArgumentParser(parents=[BasicArgs], add_help=False)


def load_plugin(path, plugin):
    p = None
    for loader, modname, is_pkg in pkgutil.iter_modules([path]):
        if modname == plugin:
            p = loader.find_module(modname).load_module(modname)
            p = p.Plugin

    return p


def setup_logging(args):
    loglevel = logging.getLevelName(LOGLEVEL)

    if args.debug:
        loglevel = logging.DEBUG

    console = logging.StreamHandler()
    logging.getLogger('').setLevel(loglevel)
    console.setFormatter(logging.Formatter(LOG_FORMAT))
    logging.getLogger('').addHandler(console)


def setup_signals(name):
    logger = logging.getLogger(__name__)

    def sigterm_handler(_signo, _stack_frame):
        logger.info('SIGTERM Caught for {}, shutting down...'.format(name))
        raise SystemExit

    signal.signal(signal.SIGTERM, sigterm_handler)
