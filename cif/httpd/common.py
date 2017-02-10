from flask import request, jsonify
import re
import zlib
from base64 import b64encode

VALID_FILTERS = ['indicator', 'itype', 'confidence', 'provider', 'limit', 'application', 'nolog', 'tags', 'days',
                 'hours', 'groups']
TOKEN_FILTERS = ['username', 'token']


def pull_token():
    t = None
    if request.headers.get("Authorization"):
        t = re.match("^Token token=(\S+)$", request.headers.get("Authorization")).group(1)
    return t


def request_v2():
    if request.headers.get('Accept'):
        if 'vnd.cif.v2+json' in request.headers['Accept']:
            return True


def jsonify_unauth(msg='unauthorized'):
    response = jsonify({
        "message": msg,
        "data": []
    })
    response.status_code = 401
    return response


def jsonify_unknown(msg='failed', code=503):
    response = jsonify({
        "message": msg,
        "data": []
    })
    response.status_code = code
    return response


def jsonify_success(data=[], code=200):
    response = jsonify({
        'message': 'success',
        'data': data
    })
    response.status_code = code
    return response


def response_compress():
    if request.args.get('gzip'):
        return True

    if request.args.get('zip'):
        return True

    if request.args.get('compress'):
        return True

    if request.headers.get('Accept-Encoding') and 'gzip' in request.headers['Accept-Encoding']:
        return True


def compress(data):
    data = zlib.compress(data)
    data = b64encode(data)
    return data


def aggregate(data, field='indicator', sort='confidence', sort_secondary='reporttime'):
    x = set()
    rv = []
    for d in sorted(data, key=lambda x: x[sort], reverse=True):
        if d[field] not in x:
            x.add(d[field])
            rv.append(d)

    rv = sorted(rv, key=lambda x: x[sort_secondary], reverse=True)
    return rv
