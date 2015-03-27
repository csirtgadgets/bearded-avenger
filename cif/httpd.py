#!/usr/bin/env python

from flask import Flask, session, redirect, url_for, escape, request, jsonify, abort, g
from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter
import logging
import textwrap
import re

from pprint import pprint
import zmq


from cif.constants import LOG_FORMAT
from cif.client import ZMQClient as zClient

# https://github.com/mitsuhiko/flask/blob/master/examples/minitwit/minitwit.py

app = Flask(__name__)
logger = logging.getLogger(__name__)


def pull_token():
    pprint(request.headers)
    token = re.match("^Token token=(\S+)$", request.headers.get("Authorization")).group(1)
    return token

@app.before_request
def before_request():
    t = pull_token()
    if not t or t == 'None':
        return '', 401

@app.route("/")
def help():
    pprint(request)
    return jsonify({
        "message": "hello world!",
    })

@app.route("/ping", methods=['GET', 'POST'])
def ping():
    r = zClient(token=pull_token).ping()
    return jsonify({
        "message": "success",
        "data": r
    })

# http://flask.pocoo.org/docs/0.10/api/#flask.Request
@app.route("/search", methods=["GET"])
def search():
    q = request.args.get('q')
    limit = request.args.get('limit')
    token = pull_token()

    r = zClient(token=token).search(str(q), limit=limit)

    return jsonify({
        "message": "success",
        "data": r
    })

@app.route("/observables", methods=["GET", "POST"])
def observables():
    token = pull_token()
    pprint(request.data)

    if request.method == "GET":
        pass
    else:
        r = zClient(token=token).send('submission', request.data)
    x = jsonify({
        "message": "success",
        "data": []
    })
    return x


def main():
    parser = ArgumentParser(
        description=textwrap.dedent('''\
        example usage:
            $ cif-httpd -d
        '''),
        formatter_class=RawDescriptionHelpFormatter,
        prog='cif-httpd'
    )

    parser.add_argument("-v", "--verbose", dest="verbose", action="count",
                        help="set verbosity level [default: %(default)s]")
    parser.add_argument('-d', '--debug', dest='debug', action="store_true")

    args = parser.parse_args()

    loglevel = logging.WARNING
    if args.verbose:
        loglevel = logging.INFO
    if args.debug:
        loglevel = logging.DEBUG

    console = logging.StreamHandler()
    logging.getLogger('').setLevel(loglevel)
    console.setFormatter(logging.Formatter(LOG_FORMAT))
    logging.getLogger('').addHandler(console)

    options = vars(args)
    app.config["SECRET_KEY"] = "ITSASECRET"
    app.run(debug=options.get('debug'))

if __name__ == "__main__":
    main()