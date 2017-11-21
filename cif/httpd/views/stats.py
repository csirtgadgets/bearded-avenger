from ..common import pull_token, jsonify_unauth, jsonify_unknown
from flask.views import MethodView
from flask import request, current_app
from cifsdk.client.zeromq import ZMQ as Client
from cif.constants import ROUTER_ADDR, PYVERSION
from cifsdk.exceptions import AuthError, InvalidSearch
import logging
from pprint import pprint

remote = ROUTER_ADDR

logger = logging.getLogger('cif-httpd')

if PYVERSION > 2:
    basestring = (str, bytes)
else:
    basestring = (str, unicode)


class StatsAPI(MethodView):
    def get(self):
        filters = {}
        for f in ['tag', 'provider', 'start', 'end']:
            if request.args.get(f):
                filters[f] = request.args.get(f)

        try:
            r = Client(remote, pull_token()).stats(filters)
        except RuntimeError as e:
            logger.error(e)
            return jsonify_unknown(msg='search failed')

        except InvalidSearch as e:
            return jsonify_unknown(msg='invalid search', code=400)

        except AuthError:
            return jsonify_unauth()

        except Exception as e:
            logger.error(e)
            return jsonify_unknown(msg='search failed, system may be too busy, check back later')

        response = current_app.response_class(r, mimetype='application/json')

        if isinstance(r, basestring):
            if '"message":"unauthorized"' in r and '"message":"unauthorized"' in r:
                response.status_code = 401
                return response

        return response
