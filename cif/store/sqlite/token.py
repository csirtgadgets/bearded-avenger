import logging
import arrow
from sqlalchemy import Column, Integer, String, DateTime, UnicodeText, Boolean, or_, ForeignKey
from sqlalchemy.orm import class_mapper, relationship, backref
from cifsdk.constants import PYVERSION
from sqlalchemy.ext.declarative import declarative_base
from cif.store.token_plugin import TokenManagerPlugin
from pprint import pprint

logger = logging.getLogger('cif.store.sqlite')

if PYVERSION > 2:
    basestring = (str, bytes)

Base = declarative_base()

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

    groups = relationship(
        'Group',
        primaryjoin='and_(Token.id==Group.token_id)',
        backref=backref('groups', uselist=True),
        lazy='subquery',
        cascade="all,delete"
    )


class Group(Base):
    __tablename__ = 'groups'
    id = Column(Integer, primary_key=True)
    group = Column(UnicodeText, index=True)

    token_id = Column(Integer, ForeignKey('tokens.id', ondelete='CASCADE'))
    token = relationship(Token)


class TokenManager(TokenManagerPlugin):

    def __init__(self, handle, engine, **kwargs):
        super(TokenManager, self).__init__(**kwargs)
        self.handle = handle
        Base.metadata.create_all(engine)

    def to_dict(self, obj):
        d = {}
        for col in class_mapper(obj.__class__).mapped_table.c:
            d[col.name] = getattr(obj, col.name)

        try:
            d['groups'] = [g.group for g in obj.groups]
        except AttributeError:
            pass

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
                self._cache[x.token]['groups'] = []
                for g in x.groups:
                    self._cache[x.token]['groups'].append(g.group)

            yield self._cache[x.token]

    def create(self, data):
        s = self.handle()

        if data.get('token') is None:
            data['token'] = self._generate()

        acl = data.get('acl')
        if type(acl) == list:
            acl = ','.join(acl)

        t = Token(
            username=data.get('username'),
            token=data['token'],
            acl=acl,
            read=data.get('read'),
            write=data.get('write'),
            expires=data.get('expires'),
            admin=data.get('admin')
        )

        s.add(t)

        groups = data.get('groups', 'everyone')
        if isinstance(groups, str):
            groups = [groups]

        for g in groups:
            gg = Group(
                group=g,
                token=t
            )
            s.add(gg)

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

        if not data.get('groups'):
            return 'groups required for updating'

        s = self.handle()
        rv = s.query(Token).filter_by(token=data['token'])
        t = rv.first()
        if not t:
            return 'token not found'

        groups = [g.group for g in t.groups]

        for g in data['groups']:
            if g in groups:
                continue

            gg = Group(
                group=g,
                token=t
            )
            s.add(gg)

        s.commit()

        # remove groups not in update
        q = s.query(Group)
        for g in groups:
            if g in data['groups']:
                continue

            rv = q.filter_by(group=g, token=t)
            if not rv.count():
                continue

            rv.delete()

        s.commit()

        return True

    def update_last_activity_at(self, token, timestamp):
        if isinstance(timestamp, str):
            timestamp = arrow.get(timestamp).datetime

        if self._cache_check(token):
            if self._cache[token].get('last_activity_at'):
                return self._cache[token]['last_activity_at']

            self._cache[token]['last_activity_at'] = timestamp
            return timestamp

        s = self.handle()
        s.query(Token).filter_by(token=token).update({Token.last_activity_at: timestamp})

        try:
            s.commit()
        except Exception as e:
            logger.error(e)
            logger.debug('rolling back transaction..')
            s.rollback()

        t = list(self.search({'token': token}))

        self._cache[token] = t[0]
        self._cache[token]['last_activity_at'] = timestamp
        return timestamp
