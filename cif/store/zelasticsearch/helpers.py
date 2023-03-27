from csirtg_indicator.utils import resolve_itype
import re
import binascii
import socket
import uuid
from hashlib import sha256
import ipaddress


def expand_ip_idx(data):
    itype = resolve_itype(data['indicator'])
    if itype not in ['ipv4', 'ipv6']:
        return

    if itype == 'ipv4':
        match = re.search(r'^(\S+)\/(\d+)$', data['indicator'])
        if match:
            data['indicator_ipv4'] = match.group(1)
            data['indicator_ipv4_mask'] = match.group(2)
            start, end, _ = cidr_to_range(data['indicator'])
            data['indicator_iprange'] = { 'gte': start, 'lte': end }
        else:
            data['indicator_ipv4'] = data['indicator']

        return

    match = re.search(r'^(\S+)\/(\d+)$', data['indicator'])
    if match:

        data['indicator_ipv6'] = binascii.b2a_hex(socket.inet_pton(socket.AF_INET6, match.group(1))).decode(
            'utf-8')
        data['indicator_ipv6_mask'] = match.group(2)
        start, end, _ = cidr_to_range(data['indicator'])
        data['indicator_iprange'] = { 'gte': start, 'lte': end }
    else:
        data['indicator_ipv6'] = binascii.b2a_hex(socket.inet_pton(socket.AF_INET6, data['indicator'])).decode(
            'utf-8')


def cidr_to_range(cidr):
    try:
        ip = ipaddress.IPv4Network(cidr)
    except Exception as e:
        ip = ipaddress.IPv6Network(cidr)

    start = str(ip.network_address)
    end = str(ip.broadcast_address)
    mask = ip.prefixlen

    return start, end, mask

def _id_random(i):
    id = str(uuid.uuid4())
    id = sha256(id.encode('utf-8')).hexdigest()
    return id


def _id_deterministic(i):
    tags = ','.join(sorted(i['tags']))
    groups = ','.join(sorted(i['group']))

    id = ','.join([groups, i['provider'], i['indicator'], tags])
    ts = i.get('reporttime')
    ts = i.get('lasttime')
    if ts:
        id = '{},{}'.format(id, ts)

    return id


def i_to_id(i):
    #id = _id_random(i)
    id = _id_deterministic(i)
    return sha256(id.encode('utf-8')).hexdigest()
