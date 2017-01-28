from flask import jsonify
from flask.views import MethodView

CMAP = {
    10: 'Certain',
    9: 'Highly Confident',
    8: 'Very Confident',
    7: 'Confident',
    6: 'Slightly better than a coin flip',
    5: 'Coin Flip',
    4: 'Slightly worse than a coin flip',
    3: 'Not Confident',
    2: 'Unknown',
    1: 'Unknown',
    0: 'Unknown',
}


class ConfidenceAPI(MethodView):

    def get(self):
        return jsonify(CMAP)
