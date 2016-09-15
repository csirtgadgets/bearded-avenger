import dns.resolver
from dns.resolver import NoAnswer, NXDOMAIN, NoNameservers
from dns.name import EmptyLabel


def resolve_ns(data, t='A'):
    try:
        answers = dns.resolver.query(data, t)
        resp = []
        for rdata in answers:
            resp.append(rdata)
    except (NoAnswer, NXDOMAIN, EmptyLabel, NoNameservers):
        return []

    return resp
