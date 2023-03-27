from flask.views import MethodView
from flask import flash
from flask import request, render_template, session
from cifsdk.client.zeromq import ZMQ as Client
from cif.constants import ROUTER_ADDR
import logging
import arrow

remote = ROUTER_ADDR

logger = logging.getLogger('cif-httpd')


class IndicatorsUI(MethodView):
    def get(self):
        session['filters'] = {}
        now = arrow.utcnow()

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
        if request.args.get('starttime') or request.args.get('endtime'):
            if request.args.get('starttime'):
                starttime = request.args.get('starttime') + 'T00:00:00Z'
            else:
                starttime = '1900-01-01T00:00:00Z'
            if request.args.get('endtime'):
                endtime = request.args.get('endtime') + 'T23:59:59Z'
            else:
                endtime = '{0}Z'.format(now.format('YYYY-MM-DDT23:59:59'))

            session['filters']['reporttime'] = '%s,%s' % (starttime, endtime)

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
        filters['groups'] = session['filters'].get('group')
    if session['filters'].get('tags'):
        filters['tags'] = session['filters'].get('tags')
    if session['filters'].get('reporttime'):
        filters['reporttime'] = session['filters'].get('reporttime')

    filters['find_relatives'] = True

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
