from sqlalchemy.orm import sessionmaker, relationship, backref, class_mapper
from sqlalchemy import Column, Date, Integer, String, Float, ForeignKey, create_engine, DateTime
from sqlalchemy.ext.declarative import declarative_base
from cif.store import Store
import logging
import arrow

DB_FILE = 'cif.db'
Base = declarative_base()

class Observable(Base):
    __tablename__ = "observables"

    id = Column(Integer, primary_key=True)
    observable = Column(String)
    group = Column(String)
    otype = Column(String)
    tlp = Column(String)
    provider = Column(String)
    portlist = Column(String)
    asn_desc = Column(String)
    asn = Column(Float)
    cc = Column(String)
    protocol = Column(Integer)
    reporttime = Column(DateTime)
    firsttime = Column(DateTime)
    lasttime= Column(DateTime)
    confidence = Column(Float)

    def __init__(self, observable=None, otype=None, tlp=None, provider=None, portlist=None, asn=None, asn_desc=None,
                 cc=None, protocol=None, firsttime=arrow.utcnow().datetime, lasttime=arrow.utcnow().datetime, reporttime=arrow.utcnow().datetime, group="everyone", tags=[], confidence=None):

        self.observable = observable
        self.group = group
        self.otype = otype
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


class Tag(Base):
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True)
    tag = Column(String)

    observable_id = Column(Integer, ForeignKey('observables.id'))
    observable = relationship(
        Observable,
        backref=backref('observables',
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

        self.logger.debug(self.path)

    def _as_dict(self, obj):
        return dict((col.name, getattr(obj, col.name))
            for col in class_mapper(obj.__class__).mapped_table.c)

    def search(self, filters):
        self.logger.debug('running search')
        return [self._as_dict(x)
                for x in self.handle().query(Observable).filter(Observable.observable == filters["observable"]).all()]

    def submit(self, data):
        if type(data) == dict:
            data = [data]

        s = self.handle()

        for d in data:
            o = Observable(**d)

            s.add(o)

            tags = d.get("tags", [])
            if isinstance(tags, basestring):
                tags = tags.split(',')

            for t in tags:
                t = Tag(tag=t, observable=o)
                s.add(t)

        s.commit()
        self.logger.debug('oid: {}'.format(o.id))
        return o.id


Plugin = SQLite

if __name__ == '__main__':
    c = SQLite()
    c.submit({
        'observable': 'example.com',
        'tags': ['botnet'],
    })