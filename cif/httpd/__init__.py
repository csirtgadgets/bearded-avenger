#!/usr/bin/env python

import logging
import os
import traceback
import textwrap
from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter

from flask import Flask, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from cif.constants import ROUTER_ADDR, RUNTIME_PATH
from cifsdk.utils import get_argument_parser, setup_logging, setup_signals, setup_runtime_path
from .common import pull_token
from .views.ping import PingAPI
from .views.help import HelpAPI
from .views.tokens import TokensAPI
from .views.indicators import IndicatorsAPI
from .views.feed import FeedAPI
from .views.confidence import ConfidenceAPI

HTTP_LISTEN = '127.0.0.1'
HTTP_LISTEN = os.environ.get('CIF_HTTPD_LISTEN', HTTP_LISTEN)

HTTP_LISTEN_PORT = 5000
HTTP_LISTEN_PORT = os.environ.get('CIF_HTTPD_LISTEN_PORT', HTTP_LISTEN_PORT)

LIMIT_MIN = os.getenv('CIF_HTTPD_LIMIT_MINUTE', 120)

PIDFILE = os.getenv('CIF_HTTPD_PIDFILE', '{}/cif_httpd.pid'.format(RUNTIME_PATH))

app = Flask(__name__)
remote = ROUTER_ADDR
logger = logging.getLogger(__name__)
limiter = Limiter(
    app,
    key_func=get_remote_address,
    global_limits=[
        '{} per minute'.format(LIMIT_MIN)
    ]
)

app.add_url_rule('/', view_func=HelpAPI.as_view('/'))
app.add_url_rule('/help', view_func=HelpAPI.as_view('help'))
app.add_url_rule('/ping', view_func=PingAPI.as_view('ping'))
app.add_url_rule('/tokens', view_func=TokensAPI.as_view('tokens'))
app.add_url_rule('/indicators', view_func=IndicatorsAPI.as_view('indicators'))
app.add_url_rule('/search', view_func=IndicatorsAPI.as_view('search'))
app.add_url_rule('/feed', view_func=FeedAPI.as_view('feed'))
app.add_url_rule('/help/confidence', view_func=ConfidenceAPI.as_view('confidence'))


@app.before_request
def before_request():
    """
    Grab the API token from headers

    :return: 401 if no token is present
    """
    if request.endpoint not in ['/', 'help', 'confidence']:
        t = pull_token()
        if not t or t == 'None':
            return '', 401


def main():
    p = get_argument_parser()
    p = ArgumentParser(
        description=textwrap.dedent('''\
        example usage:
            $ cif-httpd -d
        '''),
        formatter_class=RawDescriptionHelpFormatter,
        prog='cif-httpd',
        parents=[p]
    )
    router_address = app.config.get('CIF_ROUTER_ADDR', ROUTER_ADDR)

    p.add_argument("--router", help="specify router frontend [default %(default)s]", default=router_address)
    p.add_argument('--listen', help='specify the interface to listen on [default %(default)s]', default=HTTP_LISTEN)
    p.add_argument('--listen-port', help='specify the port to listen on [default %(default)s]',
                   default=HTTP_LISTEN_PORT)
    p.add_argument('--pidfile', help='specify pidfile location [default: %(default)s]', default=PIDFILE)

    p.add_argument('--fdebug', action='store_true')

    args = p.parse_args()
    setup_logging(args)
    logger = logging.getLogger(__name__)
    logger.info('loglevel is: {}'.format(logging.getLevelName(logger.getEffectiveLevel())))

    setup_signals(__name__)

    setup_runtime_path(args.runtime_path)

    # http://stackoverflow.com/a/789383/7205341
    pid = str(os.getpid())
    logger.debug("pid: %s" % pid)

    if os.path.isfile(args.pidfile):
        logger.critical("%s already exists, exiting" % args.pidfile)
        raise SystemExit

    try:
        pidfile = open(args.pidfile, 'w')
        pidfile.write(pid)
        pidfile.close()
    except PermissionError as e:
        logger.error('unable to create pid %s' % args.pidfile)

    try:
        logger.info('pinging router...')
        app.config["SECRET_KEY"] = os.urandom(1024)
        logger.info('starting up...')
        app.run(host=args.listen, port=args.listen_port, debug=args.fdebug, threaded=True)

    except KeyboardInterrupt:
        logger.info('shutting down...')

    except Exception as e:
        logger.critical(e)
        traceback.print_exc()

    if os.path.isfile(args.pidfile):
        os.unlink(args.pidfile)

if __name__ == "__main__":
    main()
