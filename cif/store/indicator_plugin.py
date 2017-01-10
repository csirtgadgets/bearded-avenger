import arrow


class IndicatorManagerPlugin(object):

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