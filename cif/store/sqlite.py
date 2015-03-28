from sqlalchemy.orm import sessionmaker, relationship, backref, session
from sqlalchemy import Column, Date, Integer, String, Float, ForeignKey, create_engine, DateTime
from sqlalchemy.ext.declarative import declarative_base
import datetime
from cif.store import Store
from pprint import pprint
import logging

Base = declarative_base()


class Observable(Base):
    __tablename__ = "observables"

    id = Column(Integer, primary_key=True)

    observable = Column(String)
    otype = Column(String)
    tlp = Column(String)
    provider = Column(String)
    portlist = Column(String)
    asn_desc = Column(String)
    asn = Column(Float)
    cc = Column(String)
    protocol = Column(Integer)
    reporttime = Column(DateTime)

    def __init__(self, observable=None, otype=None, tlp=None, provider=None, portlist=None, asn=None, asn_desc=None, cc=None, protocol=None, reporttime=None, tags=None):

        reporttime = datetime.datetime.strptime(reporttime, "%Y-%m-%dT%H:%M:%S.%fZ")

        self.observable = observable
        self.otype = otype
        self.tlp = tlp
        self.provider = provider
        self.portlist = str(portlist)
        self.asn =  asn
        self.asn_desc = asn_desc
        self.cc = cc
        self.protocol = protocol
        self.reporttime = reporttime
        self.tags = tags


class Tags(Base):
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True)

    observable_id = Column(Integer, ForeignKey('observables.id'))
    tag = Column(String)

    observable = relationship(
        Observable,
        backref=backref('observables',
                         uselist=True,
                         cascade='delete,all'))


# http://www.pythoncentral.io/sqlalchemy-orm-examples/
class SQLite(Store):

    name = 'sqlite'

    def __init__(self, logger=logging.getLogger(__name__), dbfile="cif.sqlite", autocommit=True, dictrows=True):
        self.logger = logger

        self.dbfile = dbfile
        self.autocommit = autocommit
        self.dictrows = dictrows

        self.engine = create_engine("sqlite:///{0}".format(self.dbfile))
        self.handle = sessionmaker()
        self.handle.configure(bind=self.engine)

        Base.metadata.create_all(self.engine)

    def search(self, data):
        pass

    def submit(self, data):
        o = Observable(**data)
        s = self.handle()
        try:
            s.add(o)
            s.commit()
        except Exception, err:
            self.logger.exception(err)
            return False

        return o.id

Plugin = SQLite