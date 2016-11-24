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
def factory(name):
    if name in FEED_PLUGINS:
        return FEED_PLUGINS[name]
    else:
        return None


def tag_contains_whitelist(data):
    for d in data:
        if d == 'whitelist':
            return True
