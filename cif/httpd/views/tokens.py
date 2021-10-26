from flask import request, current_app
from cifsdk.client.zeromq import ZMQ as Client
from cifsdk.exceptions import AuthError
from ..common import pull_token, jsonify_success, jsonify_unauth, jsonify_unknown
from flask.views import MethodView
from cif.constants import ROUTER_ADDR

import logging
remote = ROUTER_ADDR

TOKEN_FILTERS = ['username', 'token']
logger = logging.getLogger('cif-httpd')


class TokensAPI(MethodView):

    def get(self):
        cli = Client(remote, pull_token())
        filters = {}

        for f in TOKEN_FILTERS:
            filters[f] = request.args.get(f)

        if current_app.config.get('dummy'):
            return jsonify_success()

        try:
            r = cli.tokens_search(filters)

        except AuthError:
            return jsonify_unauth()

        except Exception as e:
            logger.error(e)
            return jsonify_unknown()

        return jsonify_success(r)

    def post(self):
        cli = Client(remote, pull_token())
        if not request.data:
            return jsonify_unknown('missing data', 400)

        if current_app.config.get('dummy'):
            return jsonify_success()

        try:
            r = cli.tokens_create(request.data)

        except AuthError:
            return jsonify_unauth()

        except Exception as e:
            logger.error(e)
            return jsonify_unknown()

        if not r:
            return jsonify_unknown('create failed', 400)

        return jsonify_success(r, code=201)

    def patch(self):
        cli = Client(remote, pull_token())
        try:
            r = cli.tokens_edit(request.data)

        except AuthError:
            return jsonify_unauth()

        except RuntimeError as e:
            return jsonify_unknown(msg=str(e))

        except Exception as e:
            logger.error(e)
            return jsonify_unknown()

        if not r:
            return jsonify_unauth()

        return jsonify_success(r)

    def delete(self):
        cli = Client(remote, pull_token())
        try:
            r = cli.tokens_delete(request.data)

        except AuthError:
            return jsonify_unauth()

        except Exception as e:
            logger.error(e)
            return jsonify_unknown()

        return jsonify_success(r)
