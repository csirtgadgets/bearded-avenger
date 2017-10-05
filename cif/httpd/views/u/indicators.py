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

        q = request.args.get('q')
        if not q:
            return render_template('indicators.html')

        filters = {}
        if q in ['ipv4', 'ipv6', 'fqdn', 'url', 'email']:
            filters['itype'] = q
        else:
            filters['indicator'] = q

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
