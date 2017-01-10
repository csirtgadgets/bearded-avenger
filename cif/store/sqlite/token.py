import logging
import arrow
from sqlalchemy import Column, Integer, String, DateTime, UnicodeText, Boolean, or_
from sqlalchemy.orm import class_mapper
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


class TokenManager(TokenPlugin):

    def __init__(self, handle, **kwargs):
        super(TokenManager, self).__init__(**kwargs)
        self.handle = handle

    def to_dict(self, obj):
        d = {}
        for col in class_mapper(obj.__class__).mapped_table.c:
            d[col.name] = getattr(obj, col.name)

        return d

    def search(self, data):
        s = self.handle().query(Token)

        for k in ['token', 'username', 'admin', 'write', 'read']:
            if data.get(k):
                s = s.filter_by(**{k: data[k]})

        s = s.filter(Token.revoked is not True)

        s = s.filter(or_(Token.expires == None, Token.expires >= arrow.utcnow().datetime))

        # update the cache
        for x in s:
            if x.token not in self._cache:
                self._cache[x.token] = self.to_dict(x)

            yield self._cache[x.token]

    def create(self, data):
        groups = data.get('groups')
        if type(groups) == list:
            groups = ','.join(groups)

        acl = data.get('acl')
        if type(acl) == list:
            acl = ','.join(acl)

        t = Token(
            username=data.get('username'),
            token=self._generate(),
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
        return self.to_dict(t)

    # http://stackoverflow.com/questions/1484235/replace-delete-field-using-sqlalchemy
    def delete(self, data):
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

    def edit(self, data):
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

    def update_last_activity_at(self, token, timestamp):
        timestamp = arrow.get(timestamp).datetime

        if self._cache_check(token):
            if self._cache[token].get('last_activity_at'):
                return self._cache[token]['last_activity_at']

            self._cache[token]['last_activity_at'] = timestamp
            return timestamp

        s = self.handle()
        s.query(Token).filter_by(token=token).update({Token.last_activity_at: timestamp})
        s.commit()

        t = list(self.search({'token': token}))

        self._cache[token] = t[0]
        self._cache[token]['last_activity_at'] = timestamp
        return timestamp
