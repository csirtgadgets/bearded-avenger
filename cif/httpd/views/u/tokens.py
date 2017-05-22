from flask.views import MethodView
from flask import redirect
from flask import request, render_template, session, url_for, flash
from cifsdk.client.zeromq import ZMQ as Client
from cif.constants import ROUTER_ADDR
import logging
import os
import json

remote = ROUTER_ADDR
HTTPD_TOKEN = os.getenv('CIF_HTTPD_TOKEN')

logger = logging.getLogger('cif-httpd')


class TokensUI(MethodView):
    def get(self, token_id):
        filters = {}

        if not session['admin']:
            filters['username'] = session['username']
        else:
            if request.args.get('q'):
                filters['username'] = request.args['q']

        if token_id and token_id != 'new':
            filters['token'] = token_id

        logger.debug(filters)

        try:
            r = Client(remote, HTTPD_TOKEN).tokens_search(filters)

        except Exception as e:
            logger.error(e)
            response = render_template('tokens/index.html')

        else:
            if token_id and token_id != 'new':
                response = render_template('tokens/show.html', records=r)
            else:
                response = render_template('tokens/index.html', records=r)

        return response

    def post(self, token_id):
        if not session['admin']:
            return redirect('/u/login', code=401)

        filters = {}
        if token_id:
            filters['token'] = token_id

        # TODO- need to search for default token values first, update those
        write = False
        if request.form.get('write') == 'on':
            write = True

        admin = False
        if request.form.get('admin') == 'on':
            admin = True

        t = {
            'token': token_id,
            'username': request.form['username'],
            'admin': admin,
            'write': write,
            'groups': request.form['groups'],
        }

        t = json.dumps(t)

        logger.debug(t)

        try:
            Client(remote, session['token']).tokens_edit(t)
        except Exception as e:
            logger.error(e)
            return render_template('tokens.html', error='search failed')

        filters = {}
        filters['username'] = request.args.get('username')

        try:
            r = Client(remote, session['token']).tokens_search(filters)

        except Exception as e:
            logger.error(e)
            flash(e, 'error')
            response = render_template('tokens.html')

        else:
            flash('success!')
            return redirect(url_for('/u/tokens'))

        return response

    def put(self, token_id):
        if not session['admin']:
            return redirect('/u/login', code=401)

        if request.form.get('username') == '':
            flash('missing username', 'error')
            return redirect('/u/tokens')

        write = False
        if request.form.get('write') == 'on':
            write = True

        admin = False
        if request.form.get('admin') == 'on':
            admin = True

        read = False
        if request.form.get('read') == 'on':
            read = True

        t = {
            'username': request.form['username'],
            'groups': request.form['groups'].split(','),
            'admin': admin,
            'write': write,
            'read': read
        }

        t = json.dumps(t)

        try:
            Client(remote, session['token']).tokens_create(t)
        except Exception as e:
            logger.error(e)
            flash(e, 'error')
            return redirect(url_for('/u/tokens'))

        filters = {}
        filters['username'] = request.args.get('username')

        try:
            r = Client(remote, session['token']).tokens_search(filters)

        except Exception as e:
            logger.error(e)
            flash(e, 'error')
            return redirect(url_for('/u/tokens'))

        flash('success', 'success')
        return redirect(url_for('/u/tokens'))



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
            flash('success', 'success')

        return redirect(url_for('/u/tokens'))