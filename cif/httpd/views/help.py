from flask import jsonify
from flask.views import MethodView


class HelpAPI(MethodView):

    def get(self):
        return jsonify({
            "GET /": 'this message',
            "GET /help": 'this message',
            "GET /u": 'browser friendly ui [login with api token]',
            "GET /help/confidence": "get a list of the defined confidence values",
            'GET /ping': 'ping the router interface',
            'GET /search?{q,limit,itype,indicator,confidence,tags,reporttime}': 'search for an indicator',
            'GET /indicators?{q,limit,indicator,confidence,tags,reporttime}': 'search for a set of indicators',
            'POST /indicators': 'post indicators to the router',
            'GET /feed?{q,limit,itype,confidence,tags,reporttime}': 'filter for a data-set, aggregate and apply respective whitelist',
            'GET /tokens?{username,token}': 'search for a set of tokens',
            'POST /tokens': 'create a token or set of tokens',
            'DELETE /tokens?{username,token}': 'delete a token or set of tokens',
            'PATCH /token': 'update a token'
        })