import logging
import arrow
from sqlalchemy import Column, Integer, String, DateTime, UnicodeText, Boolean, or_, ForeignKey
from sqlalchemy.orm import class_mapper, relationship, backref
from cifsdk.constants import PYVERSION
from sqlalchemy.ext.declarative import declarative_base
from cif.store.token_plugin import TokenManagerPlugin

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
                token_dict = self.to_dict(x)
                token_dict['groups'] = []
                for g in x.groups:
                    token_dict['groups'].append(g.group)
                self._cache[x.token] = token_dict

            yield self._cache[x.token]

    def auth_search(self, token):
        # if token dict already cached, use that
        token_str = token['token']
        if self._cache_check(token_str):
            self._update_last_activity_at(token_str, arrow.utcnow().datetime)
            token_dict = self._cache[token_str]
            # wrap in a list as expected from output of this func
            return [token_dict]

        # otherwise do a fresh lookup
        rv = list(self.search(token))
        if rv:
            self._update_last_activity_at(token_str, arrow.utcnow().datetime)

        return rv

    def create(self, data, token=None):
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
            read=int(data.get('read', 0)),
            write=int(data.get('write', 0)),
            expires=data.get('expires'),
            admin=int(data.get('admin', 0))
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

    def edit(self, data, bulk=False, token=None):
        dicts = []
        if bulk:
            for token_str in data:
                token_dict = data[token_str]
                try:
                    token_dict.pop('id') # don't want to save dict id back to db
                    token_dict.pop('version') # don't save dict version back to db
                except KeyError as e:
                    pass

                dicts.append(token_dict)

        else:
            dicts.append(data)

        for data in dicts:

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
