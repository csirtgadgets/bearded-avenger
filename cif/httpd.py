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

# https://github.com/mitsuhiko/flask/blob/master/examples/minitwit/minitwit.py

app = Flask(__name__)
logger = logging.getLogger(__name__)
remote = FRONTEND_ADDR


def pull_token():
    token = re.match("^Token token=(\S+)$", request.headers.get("Authorization")).group(1)
    return token

@app.before_request
def before_request():
    t = pull_token()
    if not t or t == 'None':
        return '', 401

@app.route("/")
def help():
    return jsonify({
        "message": "hello world!",
    })

@app.route("/ping", methods=['GET'])
def ping():
    r = Client(remote, pull_token()).ping()
    return jsonify({
        "message": "success",
        "data": r
    })

# http://flask.pocoo.org/docs/0.10/api/#flask.Request
@app.route("/search", methods=["GET"])
def search():
    q = request.args.get('q')
    limit = request.args.get('limit')
    filters = request.args.get('filters') or {}

    r = Client(remote, pull_token()).search(str(q), limit=limit, filters=filters)

    return jsonify({
        "message": "success",
        "data": r
    })


@app.route("/indicators", methods=["POST"])
def indicators():
    r = Client(remote, pull_token()).submit(request.data)
    return jsonify({
        "message": "success",
        "data": r
    })


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
    p.add_argument("--token", default=TOKEN)

    args = p.parse_args()
    setup_logging(args)
    logger = logging.getLogger(__name__)

    try:
        logger.info('pinging router...')
        if Client(args.router, args.token).ping():
            app.config["SECRET_KEY"] = "ITSASECRET"
            logger.info('starting up...')
            app.run()
        else:
            logger.error('router unavailable...')
    except KeyboardInterrupt:
        logger.info('shutting down...')
        raise SystemExit

if __name__ == "__main__":
    main()
