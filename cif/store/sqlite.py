import logging
import os

import arrow
from sqlalchemy import Column, Integer, String, Float, ForeignKey, create_engine, DateTime, UnicodeText, \
    Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, backref, class_mapper

from cif.constants import RUNTIME_PATH, SEARCH_CONFIDENCE
from cif.store import Store
from cif.utils import resolve_itype
import json
from cif.exceptions import AuthError
from pprint import pprint

DB_FILE = os.path.join(RUNTIME_PATH, 'cif.sqlite')
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


class Indicator(Base):
    __tablename__ = "indicators"

    id = Column(Integer, primary_key=True)
    indicator = Column(Text)
    group = Column(String)
    itype = Column(String)
    tlp = Column(String)
    provider = Column(String)
    portlist = Column(String)
    asn_desc = Column(UnicodeText)
    asn = Column(Float)
    cc = Column(String)
    protocol = Column(Integer)
    reporttime = Column(DateTime)
    firsttime = Column(DateTime)
    lasttime= Column(DateTime)
    confidence = Column(Float)
    timezone = Column(String)
    city = Column(String)
    longitude = Column(String)
    latitude = Column(String)
    peers = Column(String)
    description = Column(UnicodeText)
    additional_data = Column(UnicodeText)

    tags = relationship('Tag', primaryjoin='and_(Indicator.id==Tag.indicator_id)')

    def __init__(self, indicator=None, itype=None, tlp=None, provider=None, portlist=None, asn=None, asn_desc=None,
                 cc=None, protocol=None, firsttime=None, lasttime=None,
                 reporttime=None, group="everyone", tags=[], confidence=None,
                 reference=None, reference_tlp=None, application=None, timezone=None, city=None, longitude=None,
                 latitude=None, peers=None, description=None, additional_data=None, **kvargs):

        self.indicator = indicator
        self.group = group
        self.itype = itype
        self.tlp = tlp
        self.provider = provider
        self.portlist = str(portlist)
        self.asn = asn
        self.asn_desc = asn_desc
        self.cc = cc
        self.protocol = protocol
        self.reporttime = reporttime
        self.firsttime = firsttime
        self.lasttime = lasttime
        self.tags = tags
        self.confidence = confidence
        self.reference = reference
        self.reference_tlp = reference_tlp
        self.timezone = timezone
        self.city = city
        self.longitude = longitude
        self.latitude = latitude
        self.peers = peers
        self.description = description
        self.additional_data = additional_data

        ## TODO - cleanup for py3

        if self.reporttime and isinstance(self.reporttime, str) or isinstance(self.reporttime, unicode):
            self.reporttime = arrow.get(self.reporttime).datetime

        if self.lasttime and isinstance(self.lasttime, str) or isinstance(self.lasttime, unicode):
            self.lasttime = arrow.get(self.lasttime).datetime

        if self.firsttime and isinstance(self.firsttime, str) or isinstance(self.firsttime, unicode):
            self.firsttime = arrow.get(self.firsttime).datetime

        if self.peers:
            self.peers = json.dumps(self.peers)

        if self.additional_data:
            self.additional_data = json.dumps(self.additional_data)


class Tag(Base):
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True)
    tag = Column(String)

    indicator_id = Column(Integer, ForeignKey('indicators.id'))
    indicator = relationship(
        Indicator,
        cascade='all,delete',
        backref=backref('indicators',
                         uselist=True,
                         cascade='delete,all'))


# http://www.pythoncentral.io/sqlalchemy-orm-examples/
class SQLite(Store):

    name = 'sqlite'

    def __init__(self, dbfile=DB_FILE, autocommit=False, dictrows=True):
        self.logger = logging.getLogger(__name__)

        self.dbfile = dbfile
        self.autocommit = autocommit
        self.dictrows = dictrows
        self.path = "sqlite:///{0}".format(self.dbfile)

        self.engine = create_engine(self.path)
        self.handle = sessionmaker()
        self.handle.configure(bind=self.engine)

        Base.metadata.create_all(self.engine)

        self.logger.debug('database path: {}'.format(self.path))

    def _as_dict(self, obj):
        #return dict((col.name, getattr(obj, col.name))
        #    for col in class_mapper(obj.__class__).mapped_table.c)
        d = {}
        for col in class_mapper(obj.__class__).mapped_table.c:
            d[col.name] = getattr(obj, col.name)
            if d[col.name] and col.name.endswith('time'):
                d[col.name] = getattr(obj, col.name).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
            d[col.name] = d[col.name]

        try:
            d['tags'] = [t.tag for t in obj.tags]
        except AttributeError:
            pass

        return d

    def _log_search(self, d):
        self.submit({
            'indicator': d,
            'reporttime': arrow.utcnow().datetime,
            'tlp': 'green',
            'tags': 'search',
            'itype': resolve_itype(d),
            'confidence': SEARCH_CONFIDENCE
        })
        return True

    # TODO - normalize this out into filters
    def search(self, token, filters, limit=5):
        self.logger.debug('running search')

        if filters.get('limit'):
            limit = filters['limit']
            del filters['limit']

        if filters.get('nolog'):
            del filters['nolog']

        sql = []
        for k in filters:
            if filters[k] is not None:
                sql.append("{} = '{}'".format(k, filters[k]))

        sql = ' AND '.join(sql)

        self.logger.debug('running filter of itype')

        return [self._as_dict(x)
                for x in self.handle().query(Indicator).filter(sql).limit(limit)]

    def submit(self, token, data):
        if self.token_write(token):
            if type(data) == dict:
                data = [data]

            self.logger.debug(data)
            s = self.handle()

            for d in data:
                # namespace conflict with related self.tags
                tags = d.get("tags", [])
                if len(tags) > 0:
                    if isinstance(tags, str):
                        tags = tags.split(',')

                    del d['tags']
                o = Indicator(**d)

                s.add(o)

                if type(tags) == str:
                    tags = [tags]

                for t in tags:
                    t = Tag(tag=t, indicator=o)
                    s.add(t)

            s.commit()
            self.logger.debug('oid: {}'.format(o.id))
            return o.id
        else:
            raise AuthError('invalid token')

    def token_admin(self, token):
        x = self.handle().query(Token)\
            .filter_by(token=str(token))\
            .filter_by(admin=True)\
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
        x = self.handle().query(Token)\
            .filter_by(token=token)\
            .filter_by(read=True) \
            .filter(Token.revoked is not True)
        if x.count():
            return True

    def token_write(self, token):
        self.logger.debug('testing token: {}'.format(token))
        rv = self.handle().query(Token)\
            .filter_by(token=token)\
            .filter_by(write=True) \
            .filter(Token.revoked is not True)

        self.logger.debug(rv.count())
        if rv.count():
            return True

    def token_last_activity_at(self, token, timestamp=None):
        s = self.handle()
        if timestamp:
            x = s.query(Token).filter_by(token=token).update({Token.last_activity_at: timestamp.datetime})
            s.commit()
            if x:
                return timestamp.datetime
        else:
            x = s.query(Token).filter_by(token=token)
            if x.count():
                return x.first().last_activity_at


Plugin = SQLite