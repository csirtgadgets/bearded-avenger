#!/usr/bin/env python

import logging
import os
import textwrap
from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter

from flask import Flask, request, session, redirect, url_for, flash, render_template, _request_ctx_stack
from flask.sessions import SecureCookieSessionInterface
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_bootstrap import Bootstrap

from cif.constants import ROUTER_ADDR
from cifsdk.utils import get_argument_parser, setup_logging, setup_signals, setup_runtime_path
from .common import pull_token
from .views.ping import PingAPI
from .views.help import HelpAPI
from .views.tokens import TokensAPI
from .views.indicators import IndicatorsAPI
from .views.feed import FeedAPI
from .views.confidence import ConfidenceAPI
from .views.u.indicators import IndicatorsUI
from .views.u.tokens import TokensUI

from pprint import pprint

HTTP_LISTEN = '127.0.0.1'
HTTP_LISTEN = os.environ.get('CIF_HTTPD_LISTEN', HTTP_LISTEN)

HTTP_LISTEN_PORT = 5000
HTTP_LISTEN_PORT = os.environ.get('CIF_HTTPD_LISTEN_PORT', HTTP_LISTEN_PORT)

LIMIT_DAY = os.environ.get('CIF_HTTPD_LIMIT_DAY', 250000)
LIMIT_HOUR = os.environ.get('CIF_HTTPD_LIMIT_HOUR', 100000)

SECRET_KEY = os.getenv('CIF_HTTPD_SECRET_KEY', os.urandom(24))
HTTPD_TOKEN = os.getenv('CIF_HTTPD_TOKEN')

app = Flask(__name__)
app.secret_key = SECRET_KEY
Bootstrap(app)
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

app.add_url_rule('/u', view_func=IndicatorsUI.as_view('/u'))
app.add_url_rule('/u/search', view_func=IndicatorsUI.as_view('/u/search'))

tokens_view = TokensUI.as_view('/u/tokens')
app.add_url_rule('/u/tokens/<string:token_id>', view_func=tokens_view, methods=['GET', 'POST', 'DELETE'])
app.add_url_rule('/u/tokens/', view_func=tokens_view, defaults={'token_id': None}, methods=['GET', ])


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

    method = request.form.get('_method', '').upper()
    if method:
        request.environ['REQUEST_METHOD'] = method
        ctx = _request_ctx_stack.top
        ctx.url_adapter.default_method = method
        assert request.method == method

    print(request.method)

    if request.path == '/u/logout':
        return

    if request.path == '/u/login':
        return

    if '/u' in request.path:
        if request.remote_addr != '127.0.0.1':
            return 'unauthorized, must connect from 127.0.0.1', 401

        if 'token' not in session:
            return render_template('login.html', code=401)
        else:
            return

    if request.endpoint not in ['/', 'help', 'confidence']:

        t = pull_token()
        if not t or t == 'None':
            return '', 401


@app.route('/u/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')

    if request.method == 'POST':
        from cifsdk.client.zeromq import ZMQ as Client
        if request.form['token'] == '':
            return render_template('login.html')

        c = Client(remote, HTTPD_TOKEN)
        rv = c.tokens_search({'token': request.form['token']})
        if len(rv) == 0:
            return render_template('login.html', code=401)

        user = rv[0]

        if user['revoked']:
            return render_template('login.html', code=401)

        for k in user:
            session[k] = user[k]

        return redirect(url_for('/u/search'))


@app.route('/u/logout')
def logout():
    session.pop('token', None)
    return redirect(url_for('login'))


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
        #app.config["SECRET_KEY"] = SECRET_KEY
        logger.info('starting up...')
        app.run(host=args.listen, port=args.listen_port, debug=args.fdebug, threaded=True)

    except KeyboardInterrupt:
        logger.info('shutting down...')
        raise SystemExit

if __name__ == "__main__":
    main()
