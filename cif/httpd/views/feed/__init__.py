from ...common import pull_token, jsonify_success, jsonify_unauth, jsonify_unknown, \
    aggregate, VALID_FILTERS
from flask.views import MethodView
from flask import request, current_app, g, make_response
from cifsdk.client.zeromq import ZMQ as Client
from cifsdk.client.dummy import Dummy as DummyClient
from cif.constants import ROUTER_ADDR, HUNTER_SINK_ADDR, FEEDS_LIMIT, FEEDS_WHITELIST_LIMIT, \
    HTTPD_FEED_WHITELIST_CONFIDENCE
from cif.utils import strtobool
from cifsdk.exceptions import InvalidSearch, AuthError
import logging
import copy
import os
import time
import ujson as json

from .fqdn import Fqdn
from .ipv4 import Ipv4
from .ipv6 import Ipv6
from .url import Url
from .email import Email
from .md5 import Md5
from .sha1 import Sha1
from .sha256 import Sha256
from .sha512 import Sha512
from .ssdeep import Ssdeep

TRACE = strtobool(os.getenv('CIF_HTTPD_TRACE', False))

FEED_PLUGINS = {
    'ipv4': Ipv4,
    'ipv6': Ipv6,
    'fqdn': Fqdn,
    'url': Url,
    'email': Email,
    'md5': Md5,
    'sha1': Sha1,
    'sha256': Sha256,
    'sha512': Sha512,
    'ssdeep': Ssdeep,
}

DAYS_SHORT = 21
DAYS_MEDIUM = 45
DAYS_LONG = 90
DAYS_REALLY_LONG = 180

FEED_DAYS = {
    'ipv4': DAYS_SHORT,
    'ipv6': DAYS_SHORT,
    'url': DAYS_MEDIUM,
    'email': DAYS_MEDIUM,
    'fqdn': DAYS_MEDIUM,
    'md5': DAYS_MEDIUM,
    'sha1': DAYS_MEDIUM,
    'sha256': DAYS_MEDIUM,
    'sha512': DAYS_MEDIUM,
    'ssdeep': DAYS_REALLY_LONG,
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


log_level = logging.WARN
if TRACE:
    log_level = logging.DEBUG

console = logging.StreamHandler()
logger = logging.getLogger('gunicorn.error')
logger.setLevel(log_level)
logger.addHandler(console)

remote = ROUTER_ADDR
internal_remote = HUNTER_SINK_ADDR

class FeedAPI(MethodView):
    def get(self):
        filters = {}
        start = time.time()
        id = g.sid
        filtered_args = VALID_FILTERS.intersection(set(request.args))
        for f in filtered_args:
            # convert multiple keys of same name to single kv pair where v is comma-separated str
            # e.g., /feed?tags=malware&tags=exploit to tags=malware,exploit
            values = request.args.getlist(f)
            filters[f] = ','.join(values) 

        if len(filters) == 0:
            return jsonify_unknown('invalid search, missing an itype filter (ipv4, fqdn, url, sha1...)', 400)

        if 'itype' not in filters:
            return jsonify_unknown('missing itype filter (ipv4, fqdn, url, etc...)', 400)
        
        if filters.get('tags'):
            if 'whitelist' in filters.get('tags'):
                return jsonify_unknown('Invalid filter: tag "whitelist" is invalid for a feed. To find allow-listed indicators, perform a regular search rather than a feed pull', 
            400)
            else:
                # add a negation to ensure our search doesn't include allowlisted items
                filters['tags'] += ',!whitelist'
        else:
            filters['tags'] = '!whitelist'

        # test to make sure feed type exists
        feed_type = feed_factory(filters['itype'])
        if feed_type is None:
            err = "invalid feed itype: {}, valid types are [{}]".format(filters['itype'], '|'.join(FEED_PLUGINS))
            return jsonify_unknown(err, 400)

        if not filters.get('reporttime'):
            if not filters.get('days'):
                if not filters.get('itype'):
                    filters['days'] = DAYS_SHORT
                else:
                    filters['days'] = FEED_DAYS[filters['itype']]

        if not filters.get('limit'):
            filters['limit'] = FEEDS_LIMIT

        # for feed pulls we want values sorted first by conf DESC and second by reporttime DESC
        filters['sort'] = '-confidence,-reporttime'

        if current_app.config.get('dummy'):
            if current_app.config.get('feed'):
                r = DummyClient(remote, pull_token()).indicators_search(filters,
                                                                        decode=True,
                                                                        test_data=current_app.config['feed']['data'],
                                                                        test_wl=current_app.config['feed']['wl'])
            else:
                r = DummyClient(remote, pull_token()).indicators_search(filters)
                return jsonify_success(r)

        else:
            logger.debug('%s building feed' % id)
            logger.debug('%s getting dataset' % id)
            try:
                r = Client(remote, pull_token()).indicators_search(filters)
            except AuthError:
                return jsonify_unauth()

            except RuntimeError as e:
                return jsonify_unknown('search failed', 403)

            except InvalidSearch as e:
                logger.error(e)
                return jsonify_unknown('invalid search', 400)

            except Exception as e:
                logger.error(e)
                return jsonify_unknown(msg='search failed')

        r = aggregate(r, dedup_only=True)

        wl_filters = copy.deepcopy(filters)

        # whitelists are typically updated 1/month so we should catch those
        # esp for IP addresses
        if not wl_filters.get('days') or int(wl_filters['days']) < 45:
            wl_filters['days'] = 45
            if wl_filters.get('reporttime'):
                del wl_filters['reporttime']

        wl_filters['tags'] = 'whitelist'
        wl_filters['confidence'] = HTTPD_FEED_WHITELIST_CONFIDENCE

        wl_filters['nolog'] = True
        wl_filters['limit'] = FEEDS_WHITELIST_LIMIT
        
        # remove provider from wl_filters if exists (we don't want to narrow wl scope by provider)
        wl_filters.pop('provider', None)
        # in case anyone did something strange to get here, we couldn't want wl_filters to find IP relatives
        wl_filters.pop('find_relatives', None)

        logger.debug('gathering whitelist..')
        if current_app.config.get('feed') and current_app.config.get('feed').get('wl'):
            wl = current_app.config.get('feed').get('wl')
        else:
            try:
                wl = Client(internal_remote, pull_token()).indicators_search(wl_filters)
            except Exception as e:
                logger.error(e)
                return jsonify_unknown('feed query failed', 503)

        logger.debug('%s aggregating' % id)
        wl = aggregate(wl, dedup_only=True)

        f = feed_factory(filters['itype'])

        logger.debug('%s merging' % id)
        r = f().process(r, wl)

        logger.debug('%s done: %s' % (id, str((time.time() - start))))
        # manually make flask Response obj rather than use jsonify
        # to take advantage of ujson speed for large str
        response = make_response(json.dumps({
            "message": "success",
            "data": r
        }))

        response.headers['Content-Type'] = 'application/json'
        response.status_code = 200

        return response
