from ...common import pull_token, jsonify_success, jsonify_unauth, jsonify_unknown, compress, response_compress, \
    aggregate, VALID_FILTERS
from pprint import pprint
from flask.views import MethodView
from flask import request, current_app, jsonify
from cifsdk.client.zeromq import ZMQ as Client
from cifsdk.client.dummy import Dummy as DummyClient
from cif.constants import ROUTER_ADDR, FEEDS_DAYS, FEEDS_LIMIT, FEEDS_WHITELIST_LIMIT
from cifsdk.exceptions import InvalidSearch, AuthError
import logging
import copy

from .fqdn import Fqdn
from .ipv4 import Ipv4
from .ipv6 import Ipv6
from .url import Url
from .email import Email

FEED_PLUGINS = {
    'ipv4': Ipv4,
    'ipv6': Ipv6,
    'fqdn': Fqdn,
    'url': Url,
    'email': Email,
}


# http://stackoverflow.com/a/456747
def feed_factory(name):
    if name in FEED_PLUGINS:
        return FEED_PLUGINS[name]
    else:
        return None


def tag_contains_whitelist(data):
    for d in data:
        if d == 'whitelist':
            return True


logger = logging.getLogger('cif-httpd')
remote = ROUTER_ADDR


class FeedAPI(MethodView):
    def get(self):
        filters = {}
        for f in VALID_FILTERS:
            if request.args.get(f):
                filters[f] = request.args.get(f)

        if len(filters) == 0:
            return jsonify_unknown('invalid search, missing an itype filter (ipv4, fqdn, url, sha1...)', 400)

        # test to make sure feed type exists
        feed_type = feed_factory(filters['itype'])
        if feed_type is None:
            err = "invalid feed itype: {}, valid types are [{}]".format(filters['itype'], '|'.join(FEED_PLUGINS))
            return jsonify_unknown(err, 400)

        if not filters.get('days'):
            filters['days'] = FEEDS_DAYS

        if not filters.get('limit'):
            filters['limit'] = FEEDS_LIMIT

        if current_app.config.get('dummy'):
            r = DummyClient(remote, pull_token()).indicators_search(filters)
            return jsonify_success(r)

        try:
            r = Client(remote, pull_token()).indicators_search(filters)

        except AuthError:
            return jsonify_unauth()

        except RuntimeError as e:
            return jsonify_unknown('search failed', 403)

        except InvalidSearch as e:
            logger.error(e)
            return jsonify_unknown('invalid search', 400)

        r = aggregate(r)

        wl_filters = copy.deepcopy(filters)
        wl_filters['tags'] = 'whitelist'
        wl_filters['confidence'] = 25

        wl_filters['nolog'] = True
        wl_filters['limit'] = FEEDS_WHITELIST_LIMIT

        try:
            wl = Client(remote, pull_token()).indicators_search(wl_filters)
        except Exception as e:
            logger.error(e)
            return jsonify_unknown('feed failed', 503)

        wl = aggregate(wl)

        f = feed_factory(filters['itype'])

        r = f().process(r, wl)

        response = jsonify({
            "message": "success",
            "data": r
        })

        if response_compress():
            response.data = compress(response.data)

        response.status_code = 200

        return response
