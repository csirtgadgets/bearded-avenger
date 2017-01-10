import arrow
import abc


class IndicatorManagerPlugin(object):
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def search(self, data):
        raise NotImplementedError

    @abc.abstractmethod
    def create(self, data):
        raise NotImplementedError

    @abc.abstractmethod
    def upsert(self, data):
        raise NotImplementedError

    def _timestamps_fix(self, i):
        if not i.get('lasttime'):
            i['lasttime'] = arrow.utcnow().datetime

        if not i.get('firsttime'):
            i['firsttime'] = i['lasttime']

        if not i.get('reporttime'):
            i['reporttime'] = arrow.utcnow().datetime

    def _is_newer(self, i, rec):
        if not i.get('lasttime'):
            return False

        i_last = arrow.get(i['lasttime']).datetime
        rec_last = arrow.get(rec['lasttime']).datetime

        if i_last > rec_last:
            return True