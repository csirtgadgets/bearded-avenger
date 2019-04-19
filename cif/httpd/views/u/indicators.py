from flask.views import MethodView
from flask import flash
from flask import request, render_template, session
from cifsdk.client.zeromq import ZMQ as Client
from cif.constants import ROUTER_ADDR
import json
import logging
import csv
from csirtg_indicator import Indicator
from csirtg_indicator.constants import COLUMNS
from csirtg_indicator.format import FORMATS

remote = ROUTER_ADDR

logger = logging.getLogger('cif-httpd')


class IndicatorsUI(MethodView):
    def get(self):
        session['filters'] = {}

        if request.args.get('q'):
            session['filters']['q'] = request.args.get('q')
        if request.args.get('confidence'):
            session['filters']['confidence'] = request.args.get('confidence')
        if request.args.get('provider'):
            session['filters']['provider'] = request.args.get('provider')
        if request.args.get('group'):
            session['filters']['group'] = request.args.get('group')
        if request.args.get('tags'):
            session['filters']['tags'] = request.args.get('tags')
        if request.args.get('lasttime'):
            session['filters']['lasttime'] = request.args.get('lasttime')

        if not session['filters']:
            session['filters'] = {}

        response = render_template('indicators.html')

        return response

    def post(self):
        pass


def DataTables():
    filters = {}

    if session['filters'].get('q'):
        q = session['filters'].get('q')
        if q in ['ipv4', 'ipv6', 'fqdn', 'url', 'email']:
            filters['itype'] = q
        else:
            filters['indicator'] = q

    if session['filters'].get('confidence'):
        filters['confidence'] = session['filters'].get('confidence')
    if session['filters'].get('provider'):
        filters['provider'] = session['filters'].get('provider')
    if session['filters'].get('group'):
        filters['group'] = session['filters'].get('group')
    if session['filters'].get('tags'):
        filters['tags'] = session['filters'].get('tags')
    if session['filters'].get('lasttime'):
        filters['lasttime'] = session['filters'].get('lasttime')

    if not session['filters']:
        return []

    try:
        r = Client(remote, session['token']).indicators_search(filters)

    except Exception as e:
        logger.error(e)
        flash(e, 'error')
        response = []
    else:
        response = r
    finally:
        session['filters'] = {}

    return response
