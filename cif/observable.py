import logging
import json
import time
import datetime
import re
import pytricia
from pprint import pprint

TLP = "amber"
GROUP = "everyone"

RE_IPV4 = re.compile("^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}")
RE_FQDN = re.compile("^(?:[0-9a-zA-Z-]{1,63}\.)+[a-zA-Z]{2,63}$")
RE_URL = re.compile("^(http|https|smtp|ftp|sftp):\/\/")
RE_URL_BROKEN = re.compile("^([a-z0-9.-]+[a-z]{2,63}|\b(?:\d{1,3}\.){3}\d{1,3}\b)(:(\d+))?\/+")

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

    def __init__(self, subject=None, obj=None, tlp=TLP,
                 reporttime=datetime.datetime.fromtimestamp(time.time()).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                 provider=None, group=GROUP, protocol=None, portlist=None, tags=[], asn=None,
                 asn_desc=None, cc=None, application=None, reference=None, reference_tlp=None, logger=logging.getLogger(
                __name__), *args, **kwargs):

        self.logger = logger

        if type(tags) == str:
            tags = tags.split(",")

        self.subject = subject
        self.tlp = tlp
        self.provider = provider
        self.reporttime = reporttime
        self.group = group
        self.object = obj
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

        if not obj:
            self.object = self.resolve_obj(subject)

    def is_private(self):
        if self.object and self.object == 'ipv4':
            if IPV4_PRIVATE.get(self.subject):
                return True
        return False

    def resolve_obj(self, subject):
        def _ipv4(s):
            if RE_IPV4.match(s):
                return 1

        def _fqdn(s):
            if RE_FQDN.match(s):
                return 1

        def _url(s):
            if RE_URL.match(s):
                return 1

        if _fqdn(subject):
            return 'fqdn'
        elif _ipv4(subject):
            return 'ipv4'
        elif _url(subject):
            return 'url'

    def __repr__(self):
        o = {
            "subject": self.subject,
            "object": self.object,
            "tlp": self.tlp,
            "reporttime": self.reporttime,
            "provider": self.provider,
            "portlist": self.portlist,
            "protocol": self.protocol,
            "tags": ",".join(self.tags),
            "asn": self.asn,
            "asn_desc": self.asn_desc,
            "cc": self.cc
        }
        if self.logger.getEffectiveLevel() == 10:
            return json.dumps(o, indent=4, sort_keys=True)
        else:
            return json.dumps(o, sort_keys=True)
