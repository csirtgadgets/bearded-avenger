#!/usr/bin/env python

import logging
import os
import gc
import traceback
import textwrap
from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter

from flask import Flask, request, session, redirect, url_for, render_template, _request_ctx_stack, send_from_directory, g
#from flask.ext.session import Session
from flask_limiter import Limiter
from flask_cors import CORS
from flask_limiter.util import get_remote_address
from flask_bootstrap import Bootstrap
from os import path
from cif.constants import ROUTER_ADDR, RUNTIME_PATH
from cifsdk.utils import get_argument_parser, setup_logging, setup_signals, setup_runtime_path
import zlib
import time
import uuid
from .common import pull_token
from .views.ping import PingAPI
from .views.help import HelpAPI
from .views.health import HealthAPI
from .views.tokens import TokensAPI
from .views.indicators import IndicatorsAPI
from .views.feed import FeedAPI
from .views.confidence import ConfidenceAPI
from .views.u.indicators import IndicatorsUI
from .views.u.submit import SubmitUI
from .views.u.tokens import TokensUI

from pprint import pprint

HTTP_LISTEN = '127.0.0.1'
HTTP_LISTEN = os.environ.get('CIF_HTTPD_LISTEN', HTTP_LISTEN)

TRACE = os.getenv('CIF_HTTPD_TRACE', 0)

HTTP_LISTEN_PORT = 5000
HTTP_LISTEN_PORT = os.environ.get('CIF_HTTPD_LISTEN_PORT', HTTP_LISTEN_PORT)

LIMIT_MIN = os.getenv('CIF_HTTPD_LIMIT_MINUTE', 120)

PIDFILE = os.getenv('CIF_HTTPD_PIDFILE', '{}/cif_httpd.pid'.format(RUNTIME_PATH))

# NEEDS TO BE STATIC TO WORK WITH SESSIONS
SECRET_KEY = os.getenv('CIF_HTTPD_SECRET_KEY', os.urandom(24))
HTTPD_TOKEN = os.getenv('CIF_HTTPD_TOKEN')

HTTPD_UI_HOSTS = os.getenv('CIF_HTTPD_UI_HOSTS', '127.0.0.1')
HTTPD_UI_HOSTS = HTTPD_UI_HOSTS.split(',')

HTTPD_PROXY = os.getenv('CIF_HTTPD_PROXY')

extra_dirs = ['cif/httpd/templates', ]
extra_files = extra_dirs[:]
for extra_dir in extra_dirs:
    for dirname, dirs, files in os.walk(extra_dir):
        for filename in files:
            filename = path.join(dirname, filename)
            if path.isfile(filename):
                extra_files.append(filename)


def proxy_get_remote_address():
    if HTTPD_PROXY in ['1', 1]:
        return request.access_route[-1]

    return get_remote_address()


app = Flask(__name__)
Bootstrap(app)
CORS(app, resources={r"/*": {"origins": "*"}})
app.secret_key = SECRET_KEY

remote = ROUTER_ADDR

log_level = logging.WARN
if TRACE == '1':
    log_level = logging.DEBUG
    logging.getLogger('flask_cors').level = logging.DEBUG

console = logging.StreamHandler()
logging.getLogger('gunicorn.error').setLevel(log_level)
logging.getLogger('gunicorn.error').addHandler(console)
logger = logging.getLogger('gunicorn.error')

limiter = Limiter(
    app,
    key_func=proxy_get_remote_address,
    default_limits=[
        '{} per minute'.format(LIMIT_MIN)
    ]
)


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                              'favicon.ico', mimetype='image/vnd.microsoft.icon')


app.add_url_rule('/u', view_func=IndicatorsUI.as_view('/u'))
app.add_url_rule('/u/search', view_func=IndicatorsUI.as_view('/u/search'))
app.add_url_rule('/u/submit', view_func=SubmitUI.as_view('/u/submit'))

tokens_view = TokensUI.as_view('/u/tokens')
app.add_url_rule('/u/tokens/<string:token_id>', view_func=tokens_view, methods=['GET', 'POST', 'DELETE'])
app.add_url_rule('/u/tokens/new', view_func=tokens_view, methods=['PUT'])
app.add_url_rule('/u/tokens/', view_func=tokens_view, defaults={'token_id': None}, methods=['GET', ])


app.add_url_rule('/', view_func=HelpAPI.as_view('/'))
app.add_url_rule('/help', view_func=HelpAPI.as_view('help'))
app.add_url_rule('/health', view_func=HealthAPI.as_view('health'))
app.add_url_rule('/ping', view_func=PingAPI.as_view('ping'))
app.add_url_rule('/tokens', view_func=TokensAPI.as_view('tokens'))
app.add_url_rule('/indicators', view_func=IndicatorsAPI.as_view('indicators'))
app.add_url_rule('/search', view_func=IndicatorsAPI.as_view('search'))
app.add_url_rule('/feed', view_func=FeedAPI.as_view('feed'))
app.add_url_rule('/help/confidence', view_func=ConfidenceAPI.as_view('confidence'))


@app.teardown_request
def teardown_request(exception):
    gc.collect()


@app.before_request
def decompress():
    g.request_start_time = time.time()
    g.request_time = lambda: "%.5fs" % (time.time() - g.request_start_time)
    g.sid = str(uuid.uuid4())

    if '/u/' in request.path:
        return

    if request.headers.get('Content-Encoding') and request.headers['Content-Encoding'] == 'deflate':
        logger.debug('decompressing request: %d' % len(request.data))
        request.data = zlib.decompress(request.data)
        logger.debug('content-length: %d' % len(request.data))


@app.after_request
def process_response(response):
    if '/u/' in request.path:
        return response

    if request.headers.get('Accept-Encoding') and request.headers['Accept-Encoding'] == 'deflate':
        logger.debug('compressing resp: %d' % len(response.data))
        response.data = zlib.compress(response.data)
        response.headers['Content-Encoding'] = 'deflate'

        size = len(response.data)
        response.headers['Content-Length'] = size
        if size > 1024:
            if size < (1024 * 1024):
                size = str((size / 1024)) + 'KB'
            else:
                size = str((size / 1024 / 1024)) + 'MB'
        logger.debug('content-length %s' % size)

    logger.debug(request.url)
    logger.debug('request: %s' % g.request_time())
    return response


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

    if request.path == '/u/logout':
        return

    if request.path == '/u/login':
        return

    if request.path == '/favicon.ico':
        return

    if '/u' in request.path:
        if request.remote_addr not in HTTPD_UI_HOSTS:
            return 'unauthorized, must connect from {}'.format(','.join(HTTPD_UI_HOSTS)), 401

        # make sure SECRET_KEY is set properly
        if 'token' not in session:
            return render_template('login.html', code=401)
        else:
            return

    if request.endpoint not in ['/', 'help', 'confidence', 'health']:

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

        if user.get('revoked'):
            return render_template('login.html', code=401)

        for e in ['username', 'token', 'admin', 'read', 'write', 'groups']:
            session[e] = user[e]
        return redirect(url_for('/u'))
    return render_template('login.html')


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
    p.add_argument('--pidfile', help='specify pidfile location [default: %(default)s]', default=PIDFILE)

    p.add_argument('--fdebug', action='store_true')

    args = p.parse_args()
    setup_logging(args)
    logger = logging.getLogger(__name__)
    if TRACE:
        logger.setLevel(logging.DEBUG)
    logger.info('loglevel is: {}'.format(logging.getLevelName(logger.getEffectiveLevel())))

    setup_signals(__name__)

    setup_runtime_path(args.runtime_path)

    if not args.fdebug:
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
        logger.info('starting up...')
        app.run(host=args.listen, port=args.listen_port, debug=args.fdebug, threaded=True, extra_files=extra_files)

    except KeyboardInterrupt:
        logger.info('shutting down...')

    except Exception as e:
        logger.critical(e)
        traceback.print_exc()

    if os.path.isfile(args.pidfile):
        os.unlink(args.pidfile)


if __name__ == "__main__":
    main()
