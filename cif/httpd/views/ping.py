from flask import request, current_app
from cifsdk.client.zeromq import ZMQ as Client
from cifsdk.client.dummy import Dummy as DummyClient
from cif.constants import ROUTER_ADDR
from cifsdk.exceptions import TimeoutError, AuthError
from ..common import pull_token, jsonify_unauth, jsonify_unknown, jsonify_success
from flask.views import MethodView


class PingAPI(MethodView):

    def get(self):
        remote = ROUTER_ADDR
        if current_app.config.get('CIF_ROUTER_ADDR'):
            remote = current_app.config['CIF_ROUTER_ADDR']

        write = request.args.get('write', None)

        if current_app.config.get('dummy'):
            r = DummyClient(remote, pull_token()).ping(write=write)
            return jsonify_success(r)

        try:
            r = Client(remote, pull_token()).ping(write=write)

        except TimeoutError:
            return jsonify_unknown(msg='timeout', code=408)

        except AuthError:
            return jsonify_unauth()

        if not r:
            return jsonify_unknown(503)

        return jsonify_success(r)
