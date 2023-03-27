from ..common import pull_token, jsonify_success, jsonify_unauth, jsonify_unknown, compress, response_compress, \
    VALID_FILTERS, jsonify_busy
from flask.views import MethodView
from flask import request, current_app
from cifsdk.client.zeromq import ZMQ as Client
from cifsdk.client.dummy import Dummy as DummyClient
from cif.constants import ROUTER_ADDR, PYVERSION
from cifsdk.exceptions import AuthError, TimeoutError, InvalidSearch, SubmissionFailed, CIFBusy
import logging
from cif.utils import strtobool

remote = ROUTER_ADDR

logger = logging.getLogger('cif-httpd')

if PYVERSION > 2:
    basestring = (str, bytes)
else:
    basestring = (str, unicode)


class IndicatorsAPI(MethodView):
    def get(self):
        filters = {}
        for f in VALID_FILTERS:
            if request.args.get(f):
                filters[f] = request.args.get(f)

        if request.args.get('q'):
            filters['indicator'] = request.args.get('q')
        if request.args.get('confidence'):
            filters['confidence'] = request.args.get('confidence')
        if request.args.get('provider'):
            filters['provider'] = request.args.get('provider')
        if request.args.get('group'):
            filters['group'] = request.args.get('group')
        if request.args.get('tags'):
            filters['tags'] = request.args.get('tags')
        if request.args.get('lasttime'):
            filters['lasttime'] = request.args.get('lasttime')

        if current_app.config.get('dummy'):
            r = DummyClient(remote, pull_token()).indicators_search(filters)
            return jsonify_success(r)

        try:
            with Client(remote, pull_token()) as cli:
                r = cli.indicators_search(filters, decode=False)

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

    def post(self):
        fireball = False
        nowait = request.args.get('nowait', False)

        if request.headers.get('Content-Length'):
            logger.debug('content-length: %s' % request.headers['Content-Length'])
            if int(request.headers['Content-Length']) > 5000:
                logger.info('fireball mode')
                fireball = True
        try:
            with Client(remote, pull_token()) as cli:
                r = cli.indicators_create(request.data, nowait=nowait,
                                          fireball=fireball)
            if nowait:
                r = 'pending'

        except SubmissionFailed as e:
            logger.error(e)
            return jsonify_unknown(msg='submission failed: %s' % e, code=422)

        except RuntimeError as e:
            logger.error(e)
            return jsonify_unknown(msg='submission had a runtime error, check logs for more information', code=422)

        except TimeoutError as e:
            logger.error(e)
            return jsonify_unknown('submission timed out, check logs for more information', 408)

        except CIFBusy:
            return jsonify_busy()

        except AuthError:
            return jsonify_unauth()

        except Exception as e:
            logger.error(e)
            return jsonify_unknown('submission failed with generic exception, check logs for more information', 422)

        return jsonify_success(r, code=201)

    def delete(self):
        try:
            data = request.data.decode('utf-8')
            with Client(remote, pull_token()) as cli:
                r = cli.indicators_delete(data)

        except RuntimeError as e:
            logger.error(e)
            return jsonify_unknown(msg='submission failed, check logs for more information', code=422)

        except TimeoutError as e:
            logger.error(e)
            return jsonify_unknown('submission failed, check logs for more information', 408)

        except AuthError:
            return jsonify_unauth()

        except Exception as e:
            logger.error(e)
            return jsonify_unknown('submission failed, check logs for more information', 422)

        return jsonify_success(r)
