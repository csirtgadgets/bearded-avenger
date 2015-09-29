import logging
import json
import time
import datetime
import re
import pytricia
import socket
from pprint import pprint
from urlparse import urlparse

TLP = "green"
GROUP = "everyone"

RE_IPV4 = re.compile('^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}')
# http://stackoverflow.com/a/17871737
RE_IPV6 = re.compile('(([0-9a-fA-F]{1,4}:){7,7}[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,7}:|([0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,5}(:[0-9a-fA-F]{1,4}){1,2}|([0-9a-fA-F]{1,4}:){1,4}(:[0-9a-fA-F]{1,4}){1,3}|([0-9a-fA-F]{1,4}:){1,3}(:[0-9a-fA-F]{1,4}){1,4}|([0-9a-fA-F]{1,4}:){1,2}(:[0-9a-fA-F]{1,4}){1,5}|[0-9a-fA-F]{1,4}:((:[0-9a-fA-F]{1,4}){1,6})|:((:[0-9a-fA-F]{1,4}){1,7}|:)|fe80:(:[0-9a-fA-F]{0,4}){0,4}%[0-9a-zA-Z]{1,}|::(ffff(:0{1,4}){0,1}:){0,1}((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])|([0-9a-fA-F]{1,4}:){1,4}:((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9]))')
# http://goo.gl/Cztyn2 -- probably needs more work
RE_FQDN = re.compile('^((xn--)?(--)?[a-zA-Z0-9-_]+(-[a-zA-Z0-9]+)*\.)+[a-zA-Z]{2,}(--p1ai)?$')
RE_URI_SCHEMES = re.compile('^(https?|ftp)$')

IPV4_PRIVATE = pytricia.PyTricia()
IPV4_PRIVATE_NETS = [
    "0.0.0.0/8",
    "10.0.0.0/8",
    "127.0.0.0/8",
    "192.168.0.0/16",
    "169.254.0.0/16",
    "192.0.2.0/24",
    "224.0.0.0/4",
    "240.0.0.0/5",
    "248.0.0.0/5"
]

for x in IPV4_PRIVATE_NETS:
    IPV4_PRIVATE[x] = True


class Observable(object):

    def __init__(self, observable=None, otype=None, tlp=TLP, tags=[], group=GROUP,
                 reporttime=datetime.datetime.fromtimestamp(time.time()).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                 provider=None,  protocol=None, portlist=None,  asn=None,
                 asn_desc=None, cc=None, application=None, reference=None, reference_tlp=None, logger=logging.getLogger(
                __name__), *args, **kwargs):

        self.logger = logger

        if isinstance(tags, basestring):
            tags = tags.split(",")

        self.observable = observable
        self.tlp = tlp
        self.provider = provider
        self.reporttime = reporttime
        self.group = group
        self.otype = otype
        self.protocol = protocol
        self.portlist = portlist
        self.tags = tags
        self.application = application
        self.reference = reference
        self.reference_tlp = reference_tlp

        if asn and asn.lower() == 'na':
            asn = None

        self.asn = asn

        if asn_desc and asn_desc.lower() == 'na':
            asn_desc = None

        self.asn_desc = asn_desc
        self.cc = cc

        if not otype:
            self.otype = self.resolve_obj(self.observable)

    def is_private(self):
        if self.otype and self.otype == 'ipv4':
            if IPV4_PRIVATE.get(self.observable):
                return True
        return False

    def resolve_otype(self, observable):
        return self.resolve_obj(observable)

    def resolve_obj(self, observable):
        def _ipv6(s):
            try:
                socket.inet_pton(socket.AF_INET6, s)
            except socket.error:
                if not re.match(RE_IPV6, s):
                    return False

            return True

        def _ipv4(s):
            try:
                socket.inet_pton(socket.AF_INET, s)
            except socket.error:
                if not re.match(RE_IPV4, s):
                    return False
            return True

        def _fqdn(s):
            if RE_FQDN.match(s):
                return 1

        def _url(s):
            u = urlparse(s)
            if re.match(RE_URI_SCHEMES, u.scheme):
                if _fqdn(u.netloc) or _ipv4(u.netloc) or _ipv6(u.netloc):
                    return True

        if _fqdn(observable):
            return 'fqdn'
        elif _ipv6(observable):
            return 'ipv6'
        elif _ipv4(observable):
            return 'ipv4'
        elif _url(observable):
            return 'url'

        raise NotImplementedError('unknown otype for {}'.format(observable))

    def __repr__(self):
        o = {
            "observable": self.observable,
            "otype": self.otype,
            "tlp": self.tlp,
            "reporttime": self.reporttime,
            "provider": self.provider,
            "portlist": self.portlist,
            "protocol": self.protocol,
            "tags": ",".join(self.tags),
            "asn": self.asn,
            "asn_desc": self.asn_desc,
            "cc": self.cc,
            "group": self.group
        }
        if self.logger.getEffectiveLevel() == 10:
            return json.dumps(o, indent=4, sort_keys=True)
        else:
            return json.dumps(o, sort_keys=True)
