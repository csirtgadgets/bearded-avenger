import logging
import os

import arrow
from sqlalchemy import Column, Integer, String, DateTime, UnicodeText, Boolean
from sqlalchemy.ext.declarative import declarative_base

from cifsdk.constants import RUNTIME_PATH
from cifsdk.constants import PYVERSION
from pprint import pprint
from cif.store.sqlite import Base

logger = logging.getLogger(__name__)

VALID_FILTERS = ['indicator', 'confidence', 'provider', 'itype', 'group', 'tags']

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


class TokenMixin(object):
    def token_admin(self, token):
        x = self.handle().query(Token) \
            .filter_by(token=str(token)) \
            .filter_by(admin=True) \
            .filter(Token.revoked is not True)

        if x.count():
            return True

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

    def tokens_admin_exists(self):
        rv = self.handle().query(Token).filter_by(admin=True)
        if rv.count():
            return rv.first().token

    def tokens_search(self, data):
        rv = self.handle().query(Token)
        if data.get('token'):
            rv = rv.filter_by(token=data['token'])

        if data.get('username'):
            rv = rv.filter_by(username=data['username'])

        if rv.count():
            return [self._as_dict(x) for x in rv]

        return []

    # http://stackoverflow.com/questions/1484235/replace-delete-field-using-sqlalchemy
    def tokens_delete(self, data):
        s = self.handle()

        rv = s.query(Token)
        if data.get('username'):
            rv = rv.filter_by(username=data['username'])
        if data.get('token'):
            rv = rv.filter_by(token=data['token'])

        if rv.count():
            c = rv.count()
            rv.delete()
            s.commit()
            return c
        else:
            return 0

    def token_read(self, token):
        x = self.handle().query(Token) \
            .filter_by(token=token) \
            .filter_by(read=True) \
            .filter(Token.revoked is not True)
        pprint(x.count())
        if x.count():
            return True

    def token_write(self, token):
        self.logger.debug('testing token: {}'.format(token))
        rv = self.handle().query(Token) \
            .filter_by(token=token) \
            .filter_by(write=True) \
            .filter(Token.revoked is not True)

        if rv.count():
            return True

    def token_edit(self, data):
        if not data.get('token'):
            return 'token required for updating'

        s = self.handle()
        rv = s.query(Token).filter_by(token=data['token'])

        if not rv.count():
            return 'token not found'

        rv = rv.first()

        if data.get('groups'):
            rv.groups = ','.join(data['groups'])

        s.commit()

        return True

    def token_last_activity_at(self, token, timestamp=None):
        s = self.handle()
        timestamp = arrow.get(timestamp)
        if timestamp:
            x = s.query(Token).filter_by(token=token).update({Token.last_activity_at: timestamp.datetime})
            s.commit()
            if x:
                return timestamp.datetime
        else:
            x = s.query(Token).filter_by(token=token)
            if x.count():
                return x.first().last_activity_at
