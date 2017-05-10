from flask import jsonify
from flask.views import MethodView


class HelpAPI(MethodView):

    def get(self):
        return jsonify({
            "GET /": 'this message',
            "GET /help": 'this message',
            "GET /help/confidence": "get a list of the defined confidence values",
            'GET /ping': 'ping the router interface',
            'GET /search': 'search for an indicator',
            'GET /indicators': 'search for a set of indicators',
            'POST /indicators': 'post indicators to the router',
            'GET /feed': 'filter for a data-set, aggregate and apply respective whitelist',
            'GET /tokens': 'search for a set of tokens',
            'POST /tokens': 'create a token or set of tokens',
            'DELETE /tokens': 'delete a token or set of tokens',
            'PATCH /token': 'update a token'
        })
