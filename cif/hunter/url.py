from urlparse import urlparse
import logging
import copy


class Url(object):

    def __init__(self, *args, **kv):

        self.logger = logging.getLogger(__name__)

    def process(self, i, router):
        if i.itype == 'url':
            u = urlparse(i.indicator)
            if u.netloc:
                fqdn = copy.deepcopy(i)
                fqdn.indicator = u.netloc
                fqdn.itype = 'fqdn'
                fqdn.confidence = (int(fqdn.confidence) / 2)
            self.logger.info(u.netloc)
            self.logger.debug(fqdn)

            self.logger.debug('sending to router..')
            x = router.indicator_create(fqdn)


Plugin = Url
