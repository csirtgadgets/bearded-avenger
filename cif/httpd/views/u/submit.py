from flask.views import MethodView
from flask import request, render_template, session, redirect, flash
from cif.constants import ROUTER_ADDR
import logging
from csirtg_indicator import Indicator, InvalidIndicator
from cifsdk.client.zeromq import ZMQ as Client

remote = ROUTER_ADDR

logger = logging.getLogger('cif-httpd')


class SubmitUI(MethodView):
    def get(self):

        return render_template('submit.html', groups=session['groups'])

    def post(self):
        if not session['write']:
            return redirect('/u/search', code=401)

        i = dict(request.form)
        for k in i:
            i[k] = i[k][0]

        i['provider'] = session['username']

        try:
            i = Indicator(**i)

        except InvalidIndicator as e:
            logger.error(e)
            flash(e, 'error')
            return render_template('submit.html', error='Invalid itype')

        logger.debug(i)

        try:
            r = Client(remote, session['token']).indicators_create(i)

        except Exception as e:
            logger.error(e)
            flash(e, 'error')
            response = render_template('submit.html', error='submit failed')

        else:
            flash('submission successful', 'success')
            response = render_template('submit.html', groups=session['groups'])

        return response
