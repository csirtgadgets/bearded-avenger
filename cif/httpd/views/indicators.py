from ..common import pull_token, jsonify_success, jsonify_unauth, jsonify_unknown, \
    jsonify_busy, VALID_FILTERS
from flask.views import MethodView
from flask import request, current_app
from cifsdk.client.zeromq import ZMQ as Client
from cifsdk.client.dummy import Dummy as DummyClient
from cif.constants import ROUTER_ADDR, PYVERSION
from cifsdk.exceptions import AuthError, TimeoutError, InvalidSearch, SubmissionFailed, CIFBusy
import logging
from cif.utils import strtobool
import ujson as json

remote = ROUTER_ADDR

logger = logging.getLogger('cif-httpd')

if PYVERSION > 2:
    basestring = (str, bytes)
else:
    basestring = (str, unicode)


class IndicatorsAPI(MethodView):
    def get(self):
        filters = {}
        filtered_args = VALID_FILTERS.intersection(set(request.args))
        for f in filtered_args:
            # convert multiple keys of same name to single kv pair where v is comma-separated str
            # e.g., /feed?tags=malware&tags=exploit to tags=malware,exploit
            values = request.args.getlist(f)
            filters[f] = ','.join(values)

        if request.args.get('q'):
            filters['indicator'] = request.args.get('q')
        # b/c group (singular) is not in valid_filters
        if request.args.get('group'):
            filters['group'] = request.args.get('group')

        # convert str values to bool if present, or default to True
        try:
            filters['find_relatives'] = strtobool(
                request.args.get('find_relatives', default='false')
            )
        # strtobool raises ValueError if a non-truthy value is supplied
        except ValueError:
            filters['find_relatives'] = False

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
            data = json.loads(request.data.decode('utf-8'))
            if isinstance(data, dict):
                if not data.get('indicator'):
                    raise SubmissionFailed('missing required "indicator" field')

                data = [data]

            errored_indicators = []
            indicators_to_send = []

            for indicator in data:
                if not indicator.get('indicator'):
                    errored_indicators.append(indicator)
                    continue

                indicators_to_send.append(indicator)

            if not indicators_to_send:
                raise SubmissionFailed('all indicators missing "indicator" field')
            with Client(remote, pull_token()) as cli:
                r = cli.indicators_create(request.data, nowait=nowait,
                                          fireball=fireball)
            if nowait:
                r = 'pending'
            
            if errored_indicators:
                raise SubmissionFailed(
                    'only inserted {} out of {} submitted indicators. some were missing required "indicator" field: {}'
                    .format(len(indicators_to_send), len(data), errored_indicators)
                )

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
