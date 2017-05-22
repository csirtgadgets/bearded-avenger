from cif.httpd.common import pull_token
from flask.views import MethodView
from flask import redirect, flash
from flask import request, current_app, render_template, session
from cifsdk.client.zeromq import ZMQ as Client
from cifsdk.client.dummy import Dummy as DummyClient
from cif.constants import ROUTER_ADDR, PYVERSION
from cifsdk.exceptions import AuthError, TimeoutError, InvalidSearch, SubmissionFailed, CIFBusy
import logging
from cif.httpd.views.indicators import IndicatorsAPI
from pprint import pprint

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
