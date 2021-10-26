from flask import current_app
from cifsdk.client.zeromq import ZMQ as Client
from cif.constants import HUNTER_SINK_ADDR
from cifsdk.exceptions import TimeoutError, AuthError
from ..common import jsonify_unauth, jsonify_unknown, jsonify_success
from flask.views import MethodView
import os
import gc
from flask import request
from flask_limiter.util import get_remote_address

HTTPD_TOKEN = os.getenv('CIF_HTTPD_TOKEN', False)


class HealthAPI(MethodView):
    def get(self):

        # feeds get large need to force some cleanup
        gc.collect()

        if get_remote_address() != request.access_route[-1]:
            return jsonify_unauth()

        if not HTTPD_TOKEN:
            return jsonify_success()

        remote = HUNTER_SINK_ADDR
        if current_app.config.get('CIF_ROUTER_ADDR'):
            remote = current_app.config['CIF_ROUTER_ADDR']

        try:
            r = Client(remote, HTTPD_TOKEN).ping()
            r = Client(remote, HTTPD_TOKEN).indicators_search({'indicator': 'example.com', 'nolog': '1'})
            r = True

        except TimeoutError:
            return jsonify_unknown(msg='timeout', code=408)

        except AuthError:
            return jsonify_unauth()

        if not r:
            return jsonify_unknown(503)

        return jsonify_success()
