#!/usr/bin/env python

import logging
import os
import textwrap
from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter

from flask import Flask, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from cif.constants import ROUTER_ADDR
from cifsdk.utils import get_argument_parser, setup_logging, setup_signals, setup_runtime_path
from .common import pull_token
from .views.ping import PingAPI
from .views.help import HelpAPI
from .views.tokens import TokensAPI
from .views.indicators import IndicatorsAPI
from .views.feed import FeedAPI

HTTP_LISTEN = '127.0.0.1'
HTTP_LISTEN = os.environ.get('CIF_HTTPD_LISTEN', HTTP_LISTEN)

HTTP_LISTEN_PORT = 5000
HTTP_LISTEN_PORT = os.environ.get('CIF_HTTPD_LISTEN_PORT', HTTP_LISTEN_PORT)

LIMIT_DAY = os.environ.get('CIF_HTTPD_LIMIT_DAY', 250000)
LIMIT_HOUR = os.environ.get('CIF_HTTPD_LIMIT_HOUR', 100000)

app = Flask(__name__)
remote = ROUTER_ADDR
logger = logging.getLogger(__name__)
limiter = Limiter(
    app,
    key_func=get_remote_address,
    global_limits=[
        '{} per day'.format(LIMIT_DAY),
        '{} per hour'.format(LIMIT_HOUR)
    ]
)

app.add_url_rule('/', view_func=HelpAPI.as_view('/'))
app.add_url_rule('/help', view_func=HelpAPI.as_view('help'))
app.add_url_rule('/ping', view_func=PingAPI.as_view('ping'))
app.add_url_rule('/tokens', view_func=TokensAPI.as_view('tokens'))
app.add_url_rule('/indicators', view_func=IndicatorsAPI.as_view('indicators'))
app.add_url_rule('/search', view_func=IndicatorsAPI.as_view('search'))
app.add_url_rule('/feed', view_func=FeedAPI.as_view('feed'))


@app.before_request
def before_request():
    """
    Grab the API token from headers

    :return: 401 if no token is present
    """
    if request.endpoint not in ['/', 'help']:
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

    p.add_argument('--fdebug', action='store_true')

    args = p.parse_args()
    setup_logging(args)
    logger = logging.getLogger(__name__)
    logger.info('loglevel is: {}'.format(logging.getLevelName(logger.getEffectiveLevel())))

    setup_signals(__name__)

    setup_runtime_path(args.runtime_path)

    try:
        logger.info('pinging router...')
        app.config["SECRET_KEY"] = os.urandom(1024)
        logger.info('starting up...')
        app.run(host=args.listen, port=args.listen_port, debug=args.fdebug, threaded=True)

    except KeyboardInterrupt:
        logger.info('shutting down...')
        raise SystemExit

if __name__ == "__main__":
    main()
