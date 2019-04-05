from flask.views import MethodView
from flask import flash
from flask import request, render_template, session
from cifsdk.client.zeromq import ZMQ as Client
from cif.constants import ROUTER_ADDR
import logging

remote = ROUTER_ADDR

logger = logging.getLogger('cif-httpd')


class IndicatorsUI(MethodView):
    def get(self):
        filters = {}

        if request.args.get('q'):
            q = request.args.get('q')
            if q in ['ipv4', 'ipv6', 'fqdn', 'url', 'email']:
                filters['itype'] = q
            else:
                filters['indicator'] = q

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

        if not filters:
                return render_template('indicators.html')

        try:
            r = Client(remote, session['token']).indicators_search(filters)

        except Exception as e:
            logger.error(e)
            flash(e, 'error')
            response = render_template('indicators.html', error='search failed')

        else:
            response = render_template('indicators.html', records=r)

        return response

    def post(self):
        pass
