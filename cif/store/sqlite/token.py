import logging
import arrow
from sqlalchemy import Column, Integer, String, DateTime, UnicodeText, Boolean, or_
from cifsdk.constants import PYVERSION
from pprint import pprint
from cif.store.sqlite import Base
from cif.store.token_plugin import TokenPlugin

logger = logging.getLogger(__name__)

if PYVERSION > 2:
    basestring = (str, bytes)


class Token(Base):
    __tablename__ = 'tokens'

    id = Column(Integer, primary_key=True)
    username = Column(UnicodeText)
    token = Column(String)
    expires = Column(DateTime)
    read = Column(Boolean)
    write = Column(Boolean)
    revoked = Column(Boolean)
    acl = Column(UnicodeText)
    groups = Column(UnicodeText)
    admin = Column(Boolean)
    last_activity_at = Column(DateTime)


class TokenMixin(TokenPlugin):

    def tokens_search(self, data):
        s = self.handle().query(Token)

        for k in ['token', 'username', 'admin', 'write', 'read']:
            if data.get(k):
                s = s.filter_by(**{k: data[k]})

        s = s.filter(Token.revoked is not True)

        s = s.filter(or_(Token.expires == None, Token.expires >= arrow.utcnow().datetime))

        # update the cache
        for x in s:
            if x.token not in self.token_cache:
                self.token_cache[x.token] = x.__dict__

            yield self._as_dict(x)

    def tokens_create(self, data):
        groups = data.get('groups')
        if type(groups) == list:
            groups = ','.join(groups)

        acl = data.get('acl')
        if type(acl) == list:
            acl = ','.join(acl)

        t = Token(
            username=data.get('username'),
            token=self._token_generate(),
            groups=groups,
            acl=acl,
            read=data.get('read'),
            write=data.get('write'),
            expires=data.get('expires'),
            admin=data.get('admin')
        )

        s = self.handle()
        s.add(t)
        s.commit()
        return self._as_dict(t)

    # http://stackoverflow.com/questions/1484235/replace-delete-field-using-sqlalchemy
    def tokens_delete(self, data):
        s = self.handle()

        rv = s.query(Token)
        if data.get('username'):
            rv = rv.filter_by(username=data['username'])

        if data.get('token'):
            rv = rv.filter_by(token=data['token'])

        if not rv.count():
            return 0

        c = rv.count()
        rv.delete()
        s.commit()
        return c

    def token_edit(self, data):
        if not data.get('token'):
            return 'token required for updating'

        s = self.handle()
        rv = s.query(Token).filter_by(token=data['token']).update(data)

        if not rv:
            return 'token not found'

        if data.get('groups'):
            rv.groups = ','.join(data['groups'])

        s.commit()

        return True

    def token_update_last_activity_at(self, token, timestamp):
        timestamp = arrow.get(timestamp).datetime

        if self._token_cache_check(token):
            if self.token_cache[token].get('last_activity_at'):
                return self.token_cache[token]['last_activity_at']

            self.token_cache[token]['last_activity_at'] = timestamp
            return timestamp

        s = self.handle()
        s.query(Token).filter_by(token=token).update({Token.last_activity_at: timestamp})
        s.commit()

        t = list(self.tokens_search({'token': token}))

        self.token_cache[token] = t[0]
        self.token_cache[token]['last_activity_at'] = timestamp