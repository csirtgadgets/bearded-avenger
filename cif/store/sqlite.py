from sqlalchemy.orm import sessionmaker, relationship, backref, session
from sqlalchemy import Column, Date, Integer, String, Float, ForeignKey, create_engine, DateTime
from sqlalchemy.ext.declarative import declarative_base
import datetime
from cif.store import Store
from pprint import pprint
import logging

Base = declarative_base()


class Observable(Base):
    __tablename__ = "observable"

    id = Column(Integer, primary_key=True)
    thing = Column(String)
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

    def __init__(self, observable=None, otype=None, tlp=None, provider=None, portlist=None, asn=None, asn_desc=None,
                 cc=None, protocol=None, reporttime=None, tags=None, group="everyone"):

        reporttime = datetime.datetime.strptime(reporttime, "%Y-%m-%dT%H:%M:%S.%fZ")

        self.thing = observable
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


class Tag(Base):
    __tablename__ = "tag"

    id = Column(Integer, primary_key=True)
    tag = Column(String)

    observable_id = Column(Integer, ForeignKey('observable.id'))
    observable = relationship(
        Observable,
        backref=backref('observable',
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

        self.logger.debug("sqlite:///{0}".format(self.dbfile))

    def search(self, filters):
        self.logger.debug('running search')
        s = self.handle()
        rv = s.query(Observable).filter(Observable.thing == filters["observable"]).limit(filters["limit"])
        results = []
        for x in rv.all():
            x = dict(x.__dict__); x.pop('_sa_instance_state', None)
            x["observable"] = x["thing"]
            del x["thing"]
            results.append(x)

        return results

    def submit(self, data):
        o = Observable(**data)
        tags = data.get("tags") or []
        s = self.handle()
        try:
            s.add(o)
            for t in tags.split(","):
                t = Tag(tag=t, observable=o)
                s.add(t)
            s.commit()
        except Exception, err:
            self.logger.exception(err)
            return False

        return o.id

Plugin = SQLite