#!/usr/bin/env python

from flask import Flask, request, jsonify
from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter
import logging
import textwrap
import re
import os
from cif.utils import get_argument_parser, setup_logging

from pprint import pprint


from cif.constants import FRONTEND_ADDR
from cif.client.zeromq import ZMQ as Client
TOKEN = os.environ.get('CIF_TOKEN', None)
TOKEN = os.environ.get('CIF_HTTPD_TOKEN', TOKEN)

HTTP_LISTEN = '127.0.0.1'
HTTP_LISTEN = os.environ.get('CIF_HTTP_LISTEN', HTTP_LISTEN)

HTTP_LISTEN_PORT = 5000
HTTP_LISTEN_PORT = os.environ.get('CIF_HTTP_LISTEN_PORT', HTTP_LISTEN_PORT)

FILTERS = ['itype', 'confidence', 'provider']

# https://github.com/mitsuhiko/flask/blob/master/examples/minitwit/minitwit.py

app = Flask(__name__)
remote = FRONTEND_ADDR
logger = logging.getLogger(__name__)

def pull_token():
    token = None
    if request.headers.get("Authorization"):
        token = re.match("^Token token=(\S+)$", request.headers.get("Authorization")).group(1)
    return token

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
def help():
    """
    Return a list of routes

    :return:
    """
    return jsonify({
        "GET /": 'this message',
        "GET /help": 'this message',
        'GET /ping': 'ping the router interface',
        'GET /search': 'search for an indicator',
        'POST /indicators': 'post indicators to the router',
    })

@app.route("/ping", methods=['GET'])
def ping():
    """
    Ping the router interface

    :return: { 'message': 'success', 'data': '<timestamp>' }
    """
    r = Client(remote, pull_token()).ping()
    return jsonify({
        "message": "success",
        "data": r
    })

# http://flask.pocoo.org/docs/0.10/api/#flask.Request
@app.route("/search", methods=["GET"])
def search():
    """
    Search controller

    :param q: query term (ex: example.org, 1.2.3.4, 1.2.3.0/24)
    :param limit: limit search results (reporttime desc)

    :return: { 'message': 'success', 'data': [] }
    """
    q = request.args.get('q')
    limit = request.args.get('limit')
    filters = request.args.get('filters') or {}

    r = Client(remote, pull_token()).search(str(q), limit=limit, filters=filters)

    return jsonify({
        "message": "success",
        "data": r
    })

@app.route("/indicators", methods=["GET", "POST"])
def indicators():
    """
    GET/POST the Indicators Controller

    :return: { 'message': '{success|failure}', 'data': [] }
    """
    if request.method == 'GET':
        filters = {}
        for f in FILTERS:
            if request.args.get(f):
                filters[f] = request.args.get(f)
        try:
            r = Client(remote, pull_token()).filter(filters=filters, limit=request.args.get(
                'limit'))
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
            r = Client(remote, pull_token()).submit(request.data)
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

    p.add_argument("--router", help="specify router frontend [default %(default)s]", default=FRONTEND_ADDR)
    p.add_argument('--token', help="specify cif-httpd token [default %(default)s]", default=TOKEN)
    p.add_argument('--listen', help='specify the interface to listen on [default %(default)s]', default=HTTP_LISTEN)
    p.add_argument('--listen-port', help='specify the port to listen on [default %(default)s]',
                   default=HTTP_LISTEN_PORT)

    p.add_argument('--fdebug', action='store_true')

    args = p.parse_args()
    setup_logging(args)
    logger = logging.getLogger(__name__)

    try:
        logger.info('pinging router...')
        if Client(args.router, args.token).ping():
            app.config["SECRET_KEY"] = os.urandom(1024)
            logger.info('starting up...')
            app.run(host=args.listen, port=args.listen_port, debug=args.fdebug)
        else:
            logger.error('router unavailable...')
    except KeyboardInterrupt:
        logger.info('shutting down...')
        raise SystemExit

if __name__ == "__main__":
    main()
