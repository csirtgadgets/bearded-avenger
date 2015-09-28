#!/usr/bin/env python

from flask import Flask, session, redirect, url_for, escape, request, jsonify, abort, g
from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter
import logging
import textwrap
import re

from pprint import pprint


from cif.constants import LOG_FORMAT, ROUTER_FRONTEND
from cif.client.zeromq import ZMQ as Client

# https://github.com/mitsuhiko/flask/blob/master/examples/minitwit/minitwit.py

app = Flask(__name__)
logger = logging.getLogger(__name__)
remote = ROUTER_FRONTEND


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

    r = Client(remote, pull_token()).search(str(q), limit=limit)

    return jsonify({
        "message": "success",
        "data": r
    })

@app.route("/observables", methods=["POST"])
def observables():
    r = Client(remote, pull_token()).submit(request.data)
    return jsonify({
        "message": "success",
        "data": r
    })

def main():
    p = ArgumentParser(
        description=textwrap.dedent('''\
        example usage:
            $ cif-httpd -d
        '''),
        formatter_class=RawDescriptionHelpFormatter,
        prog='cif-httpd'
    )

    p.add_argument("-v", "--verbose", dest="verbose", action="count",
                        help="set verbosity level [default: %(default)s]")
    p.add_argument('-d', '--debug', dest='debug', action="store_true")

    p.add_argument("--token", dest="token", help="specify httpd token", default="1234")
    p.add_argument("--remote", dest="remote", default=ROUTER_FRONTEND)

    args = p.parse_args()

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

    remote = options["remote"]

    try:
        if Client(remote, options["token"]).ping():
            app.config["SECRET_KEY"] = "ITSASECRET"
            #app.run(debug=options.get('debug'), passthrough_errors=True) # this changes pids so supervisord gets
            # confused
            app.run()
    except KeyboardInterrupt:
        logger.info('shutting down...')
        raise SystemExit

if __name__ == "__main__":
    main()