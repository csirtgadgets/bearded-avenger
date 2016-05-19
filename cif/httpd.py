#!/usr/bin/env python

import logging
import os
import re
import textwrap
from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter

from flask import Flask, request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from cifsdk.client.zeromq import ZMQ as Client
from cifsdk.client.dummy import Dummy as DummyClient
from cif.constants import ROUTER_ADDR
from cifsdk.constants import TOKEN
from cifsdk.utils import get_argument_parser, setup_logging, setup_signals, setup_runtime_path
from pprint import pprint
from cifsdk.exceptions import AuthError

TOKEN = os.environ.get('CIF_HTTPD_TOKEN', TOKEN)

HTTP_LISTEN = '127.0.0.1'
HTTP_LISTEN = os.environ.get('CIF_HTTPD_LISTEN', HTTP_LISTEN)

HTTP_LISTEN_PORT = 5000
HTTP_LISTEN_PORT = os.environ.get('CIF_HTTPD_LISTEN_PORT', HTTP_LISTEN_PORT)

VALID_FILTERS = ['indicator', 'itype', 'confidence', 'provider', 'limit', 'application']
TOKEN_FILTERS = ['username', 'token']

LIMIT_DAY = os.environ.get('CIF_HTTPD_LIMIT_DAY', 5000)
LIMIT_HOUR = os.environ.get('CIF_HTTPD_LIMIT_HOUR', 500)

# https://github.com/mitsuhiko/flask/blob/master/examples/minitwit/minitwit.py

app = Flask(__name__)
remote = ROUTER_ADDR
logger = logging.getLogger(__name__)
limiter = Limiter(
    app,
    key_func=get_remote_address,  # TODO change this to pull_token
    global_limits=[
        '{} per day'.format(LIMIT_DAY),
        '{} per hour'.format(LIMIT_HOUR)
    ]
)


def pull_token():
    t = None
    if request.headers.get("Authorization"):
        t = re.match("^Token token=(\S+)$", request.headers.get("Authorization")).group(1)
    return t


@app.before_request
def before_request():
    """
    Grab the API token from headers

    :return: 401 if no token is present
    """
    if request.endpoint != 'help':
        t = pull_token()
        if not t or t == 'None':
            return '', 401


@app.route("/")
@app.route("/help")
def help():
    """ Return a list of routes

    :return: str
    """
    return jsonify({
        "GET /": 'this message',
        "GET /help": 'this message',
        'GET /ping': 'ping the router interface',
        'GET /search': 'search for an indicator',
        'GET /indicators': 'search for a set of indicators',
        'POST /indicators': 'post indicators to the router',
        'GET /tokens': 'search for a set of tokens',
        'POST /tokens': 'create a token or set of tokens',
        'DELETE /tokens': 'delete a token or set of tokens',
        'PATCH /token': 'update a token'
    })


@app.route("/ping", methods=['GET'])
def ping():
    """
    Ping the router interface

    :return: { 'message': 'success', 'data': '<timestamp>' }
    """
    remote = ROUTER_ADDR
    if app.config.get('CIF_ROUTER_ADDR'):
        remote = app.config['CIF_ROUTER_ADDR']

    write = request.args.get('write', None)

    if app.config.get('dummy'):
        r = DummyClient(remote, pull_token()).ping(write=write)
    else:
        r = Client(remote, pull_token()).ping(write=write)

    resp = jsonify({
        "message": "success",
        "data": r
    })

    if not r:
        resp = jsonify({
            'message': 'failed',
            'data': [],
        })
        resp.status_code = 401

    return resp


# http://flask.pocoo.org/docs/0.10/api/#flask.Request
@app.route("/search", methods=["GET"])
def search():
    """
    Search controller

    :param str q: query term (ex: example.org, 1.2.3.4, 1.2.3.0/24)
    :param dict filters: query filters
    :param int limit: limit search results (reporttime desc)

    :return: { 'message': 'success', 'data': [] }
    """

    remote = ROUTER_ADDR
    if app.config.get('CIF_ROUTER_ADDR'):
        remote = app.config['CIF_ROUTER_ADDR']

    filters = {}
    for k in VALID_FILTERS:
        if request.args.get(k):
            filters[k] = request.args.get(k)

    if request.args.get('q'):
        filters['indicator'] = request.args.get('q')

    try:
        if app.config.get('dummy'):
            r = DummyClient(remote, pull_token()).indicators_search(filters)
        else:
            r = Client(remote, pull_token()).indicators_search(filters)
        response = jsonify({
            "message": "success",
            "data": r
        })
        response.status_code = 200
    except AuthError as e:
        response = jsonify({
            'message': 'unauthorized',
            'data': [],
            'status': 'failed'
        })
        response.status_code = 401

    return response


@app.route("/indicators", methods=["GET", "POST"])
def indicators():
    """
    GET/POST the Indicators Controller

    :return: { 'message': '{success|failure}', 'data': [] }
    """
    if request.method == 'GET':
        filters = {}
        for f in VALID_FILTERS:
            if request.args.get(f):
                filters[f] = request.args.get(f)
        try:
            if app.config.get('dummy'):
                r = DummyClient(remote, pull_token()).filter(filters=filters, limit=request.args.get('limit'))
            else:
                r = Client(remote, pull_token()).filter(filters=filters, limit=request.args.get('limit'))
        except RuntimeError as e:
            logger.error(e)
            response = jsonify({
                "message": "search failed",
                "data": []
            })
            response.status_code = 403
        else:
            response = jsonify({
                "message": "success",
                "data": r
            })
            response.status_code = 200

    else:
        try:
            logger.debug(request.data)
            r = Client(remote, pull_token()).indicator_create(request.data)
        except RuntimeError as e:
            logger.error(e)
            response = jsonify({
                "message": "submission failed",
                "data": []
            })
            response.status_code = 422
        else:
            response = jsonify({
                "message": "success",
                "data": r
            })
            response.status_code = 201

    return response


@app.route("/tokens", methods=["GET", "POST", "DELETE", "PATCH"])
def tokens():
    cli = Client(remote, pull_token())
    if request.method == 'DELETE':
        try:
            r = cli.tokens_delete(request.data)
        except Exception as e:
            logger.error(e)
            response = jsonify({
                "message": "failed",
                "data": []
            })
            response.status_code = 503
        else:
            response = jsonify({
                'message': 'success',
                'data': r
            })
            response.status_code = 200
    elif request.method == 'POST':
        if request.data:
            try:
                r = cli.tokens_create(request.data)
            except AuthError:
                response = jsonify({
                    'message': 'admin privs required',
                    'data': []
                })
                response.status_code = 401
            except Exception as e:
                logger.error(e)
                response = jsonify({
                    'message': 'create failed',
                    'data': []
                })
                response.status_code = 503
            else:
                if r:
                    response = jsonify({
                        'message': 'success',
                        'data': r
                    })
                    response.status_code = 200
                else:
                    response = jsonify({
                        'message': 'admin privs required',
                        'data': []
                    })
                    response.status_code = 401
        else:
            response = jsonify({
                'message': 'create failed',
                'data': []
            })
            response.status_code = 400
    elif request.method == 'PATCH':
        try:
            r = cli.tokens_edit(request.data)
        except AuthError:
            response = jsonify({
                'message': 'admin privs required',
                'data': []
            })
            response.status_code = 401
        except Exception as e:
            logger.error(e)
            import traceback
            traceback.print_exc()
            response = jsonify({
                'message': 'create failed',
                'data': []
            })
            response.status_code = 503
        else:
            if r:
                response = jsonify({
                    'message': 'success',
                    'data': r
                })
                response.status_code = 200
            else:
                response = jsonify({
                    'message': 'admin privs required',
                    'data': []
                })
                response.status_code = 401
    else:
        filters = {}
        for f in TOKEN_FILTERS:
            filters[f] = request.args.get(f)

        try:
            r = cli.tokens_search(filters)
        except AuthError:
            response = jsonify({
                "message": "failed",
                "data": []
            })
            response.status_code = 401
        except Exception as e:
            logger.error(e)
            response = jsonify({
                "message": "failed",
                "data": []
            })
            response.status_code = 503
        else:
            response = jsonify({
                'message': 'success',
                'data': r
            })
            response.status_code = 200

    return response


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
    p.add_argument('--token', help="specify cif-httpd token [default %(default)s]", default=TOKEN)
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
