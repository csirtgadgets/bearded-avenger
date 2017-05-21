from cif.httpd.common import pull_token
from flask.views import MethodView
from flask import redirect, flash
from flask import request, current_app, render_template, session, url_for
from cifsdk.client.zeromq import ZMQ as Client
from cifsdk.client.dummy import Dummy as DummyClient
from cif.constants import ROUTER_ADDR, PYVERSION
from cifsdk.exceptions import AuthError, TimeoutError, InvalidSearch, SubmissionFailed, CIFBusy
import logging
from cif.httpd.views.indicators import IndicatorsAPI
from pprint import pprint
import os
import json

remote = ROUTER_ADDR
HTTPD_TOKEN = os.getenv('CIF_HTTPD_TOKEN')

logger = logging.getLogger('cif-httpd')


class TokensUI(MethodView):
    def get(self, token_id):

        if not session['admin']:
            return redirect('/u/login', code=401)

        logger.debug(token_id)
        filters = {}

        if request.args.get('q'):
            filters['username'] = request.args['q']

        if token_id:
            filters['token'] = token_id

        try:
            r = Client(remote, session['token']).tokens_search(filters)

        except Exception as e:
            logger.error(e)
            response = render_template('tokens.html', error='search failed')

        else:
            response = render_template('tokens.html', records=r)

        return response

    def post(self, token_id):
        pass

    def delete(self, token_id):
        if not session['admin']:
            return redirect('/u/login', code=401)

        filters = {}
        if token_id:
            filters['token'] = token_id
            filters['username'] = None

        filters = json.dumps(filters)
        try:
            r = Client(remote, HTTPD_TOKEN).tokens_delete(filters)

        except Exception as e:
            logger.error(e)
            flash(e, 'error')
        else:
            flash('success')
        
        return redirect(url_for('/u/tokens'))