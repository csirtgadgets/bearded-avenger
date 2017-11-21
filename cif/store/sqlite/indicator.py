import os

import arrow
from sqlalchemy import Column, Integer, String, Float, DateTime, UnicodeText, desc, ForeignKey, or_, Index
from sqlalchemy.orm import relationship, backref, class_mapper, lazyload, joinedload, subqueryload

from cifsdk.constants import RUNTIME_PATH, PYVERSION
import json
from base64 import b64decode, b64encode
from csirtg_indicator import resolve_itype
from csirtg_indicator.exceptions import InvalidIndicator
from cif.store.indicator_plugin import IndicatorManagerPlugin
from cifsdk.exceptions import InvalidSearch
import ipaddress
from .ip import Ip
from .fqdn import Fqdn
from .url import Url
from .hash import Hash
from pprint import pprint
from sqlalchemy.ext.declarative import declarative_base
import re
import logging
import time

logger = logging.getLogger('cif.store.sqlite')

DB_FILE = os.path.join(RUNTIME_PATH, 'cif.sqlite')
REQUIRED_FIELDS = ['provider', 'indicator', 'tags', 'group', 'itype']
HASH_TYPES = ['sha1', 'sha256', 'sha512', 'md5']

from cif.httpd.common import VALID_FILTERS

if PYVERSION > 2:
    basestring = (str, bytes)


Base = declarative_base()


class Indicator(Base):
    __tablename__ = "indicators"

    id = Column(Integer, primary_key=True)
    indicator = Column(UnicodeText, index=True)
    group = Column(String)
    itype = Column(String, index=True)
    tlp = Column(String)
    provider = Column(String, index=True)
    portlist = Column(String)
    asn_desc = Column(UnicodeText, index=True)
    asn = Column(Float)
    cc = Column(String, index=True)
    protocol = Column(Integer)
    reporttime = Column(DateTime, index=True)
    firsttime = Column(DateTime)
    lasttime = Column(DateTime, index=True)
    confidence = Column(Float, index=True)
    timezone = Column(String)
    city = Column(String)
    longitude = Column(String)
    latitude = Column(String)
    peers = Column(UnicodeText)
    description = Column(UnicodeText)
    additional_data = Column(UnicodeText)
    rdata = Column(UnicodeText, index=True)
    count = Column(Integer)
    region = Column(String, index=True)

    tags = relationship(
        'Tag',
        primaryjoin='and_(Indicator.id==Tag.indicator_id)',
        backref=backref('tags', uselist=True),
        lazy='subquery',
        cascade="all,delete"
    )

    messages = relationship(
        'Message',
        primaryjoin='and_(Indicator.id==Message.indicator_id)',
        backref=backref('messages', uselist=True),
        lazy='subquery',
        cascade="all,delete"
    )

    def __init__(self, indicator=None, itype=None, tlp=None, provider=None, portlist=None, asn=None, asn_desc=None,
                 cc=None, protocol=None, firsttime=None, lasttime=None,
                 reporttime=None, group="everyone", confidence=None,
                 reference=None, reference_tlp=None, application=None, timezone=None, city=None, longitude=None,
                 latitude=None, peers=None, description=None, additional_data=None, rdata=None, msg=None, count=1,
                 region=None, version=None, **kwargs):

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
        self.rdata = rdata
        self.count = count
        self.region = region

        if self.reporttime and isinstance(self.reporttime, basestring):
            self.reporttime = arrow.get(self.reporttime).datetime

        if self.lasttime and isinstance(self.lasttime, basestring):
            self.lasttime = arrow.get(self.lasttime).datetime

        if self.firsttime and isinstance(self.firsttime, basestring):
            self.firsttime = arrow.get(self.firsttime).datetime

        if self.peers is not None:
            self.peers = json.dumps(self.peers)

        if self.additional_data is not None:
            self.additional_data = json.dumps(self.additional_data)


class Ipv4(Base):
    __tablename__ = 'indicators_ipv4'

    id = Column(Integer, primary_key=True)
    ipv4 = Column(Ip, index=True)
    mask = Column(Integer, default=32)

    indicator_id = Column(Integer, ForeignKey('indicators.id', ondelete='CASCADE'))
    indicator = relationship(
        Indicator,
    )


class Ipv6(Base):
    __tablename__ = 'indicators_ipv6'

    id = Column(Integer, primary_key=True)
    ip = Column(Ip(version=6), index=True)
    mask = Column(Integer, default=64)

    indicator_id = Column(Integer, ForeignKey('indicators.id', ondelete='CASCADE'))
    indicator = relationship(
        Indicator,
    )


class Fqdn(Base):
    __tablename__ = 'indicators_fqdn'

    id = Column(Integer, primary_key=True)
    fqdn = Column(Fqdn, index=True)

    indicator_id = Column(Integer, ForeignKey('indicators.id', ondelete='CASCADE'))
    indicator = relationship(
        Indicator,
    )


class Url(Base):
    __tablename__ = 'indicators_url'

    id = Column(Integer, primary_key=True)
    url = Column(Url, index=True)

    indicator_id = Column(Integer, ForeignKey('indicators.id', ondelete='CASCADE'))
    indicator = relationship(
        Indicator,
    )


class Hash(Base):
    __tablename__ = 'indicators_hash'

    id = Column(Integer, primary_key=True)
    hash = Column(Hash, index=True)

    indicator_id = Column(Integer, ForeignKey('indicators.id', ondelete='CASCADE'))
    indicator = relationship(
        Indicator,
    )


class Tag(Base):
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True)
    tag = Column(String, index=True)

    indicator_id = Column(Integer, ForeignKey('indicators.id', ondelete='CASCADE'))
    indicator = relationship(
        Indicator,
    )

    __table_args__ = (Index('ix_tags_indicator', "tag", "indicator_id"),)


class Message(Base):
    __tablename__ = 'messages'

    id = Column(Integer, primary_key=True)
    message = Column(UnicodeText)

    indicator_id = Column(Integer, ForeignKey('indicators.id', ondelete='CASCADE'))
    indicator = relationship(
        Indicator,
    )


class IndicatorManager(IndicatorManagerPlugin):

    def __init__(self, handle, engine, **kwargs):
        super(IndicatorManager, self).__init__(**kwargs)

        self.handle = handle
        Base.metadata.create_all(engine)

    def to_dict(self, obj):
        d = {}
        for col in class_mapper(obj.__class__).mapped_table.c:
            d[col.name] = getattr(obj, col.name)
            if d[col.name] and col.name.endswith('time'):
                d[col.name] = getattr(obj, col.name).strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        try:
            d['tags'] = [t.tag for t in obj.tags]
        except AttributeError:
            pass

        try:
            d['message'] = [b64encode(m.message) for m in obj.messages]
        except AttributeError:
            pass

        return d

    def test_valid_indicator(self, i):
        if isinstance(i, Indicator):
            i = i.__dict__()

        for f in REQUIRED_FIELDS:
            if not i.get(f):
                raise InvalidIndicator("Missing required field: {} for \n{}".format(f, i))

    def create(self, token, data):
        return self.upsert(token, data)

    def _filter_indicator(self, filters, s):

        for k, v in list(filters.items()):
            if k not in VALID_FILTERS:
                del filters[k]

        if not filters.get('indicator'):
            return s

        i = filters.pop('indicator')
        if PYVERSION == 2:
            if isinstance(i, str):
                i = unicode(i)

        try:
            itype = resolve_itype(i)
        except InvalidIndicator as e:
            logger.error(e)
            s = s.join(Message).filter(Indicator.Message.like('%{}%'.format(i)))
            return s

        if itype in ['email']:
            s = s.filter(Indicator.indicator == i)
            return s

        if itype == 'ipv4':
            ip = ipaddress.IPv4Network(i)
            mask = ip.prefixlen

            if mask < 8:
                raise InvalidSearch('prefix needs to be >= 8')

            start = str(ip.network_address)
            end = str(ip.broadcast_address)

            logger.debug('{} - {}'.format(start, end))

            s = s.join(Ipv4).filter(Ipv4.ipv4 >= start)
            s = s.filter(Ipv4.ipv4 <= end)

            return s

        if itype == 'ipv6':
            ip = ipaddress.IPv6Network(i)
            mask = ip.prefixlen

            if mask < 32:
                raise InvalidSearch('prefix needs to be >= 32')

            start = str(ip.network_address)
            end = str(ip.broadcast_address)

            logger.debug('{} - {}'.format(start, end))

            s = s.join(Ipv6).filter(Ipv6.ip >= start)
            s = s.filter(Ipv6.ip <= end)
            return s

        if itype == 'fqdn':
            s = s.join(Fqdn).filter(or_(
                    Fqdn.fqdn.like('%.{}'.format(i)),
                    Fqdn.fqdn == i)
            )
            return s

        if itype == 'url':
            s = s.join(Url).filter(Url.url == i)
            return s

        if itype in HASH_TYPES:
            s = s.join(Hash).filter(Hash.hash == str(i))
            return s

        raise InvalidIndicator

    def _filter_terms(self, filters, s):

        # TODO also you should do for k, v in filters.items():
        # iteritems()?
        for k in filters:
            if k in ['nolog', 'days', 'hours', 'groups', 'limit']:
                continue

            if k == 'reporttime':
                if ',' in filters[k]:
                    start, end = filters[k].split(',')
                    s = s.filter(Indicator.reporttime >= arrow.get(start).datetime)
                    s = s.filter(Indicator.reporttime <= arrow.get(end).datettime)
                else:
                    s = s.filter(Indicator.reporttime >= arrow.get(filters[k]).datetime)

            elif k == 'reporttimeend':
                s = s.filter(Indicator.reporttime <= filters[k])

            elif k == 'tags':
                s = s.outerjoin(Tag).filter(Tag.tag == filters[k])

            elif k == 'confidence':
                if ',' in str(filters[k]):
                    start, end = str(filters[k]).split(',')
                    s = s.filter(Indicator.confidence >= float(start))
                    s = s.filter(Indicator.confidence <= float(end))
                else:
                    s = s.filter(Indicator.confidence >= float(filters[k]))

            elif k == 'itype':
                s = s.filter(Indicator.itype == filters[k])

            elif k == 'provider':
                s = s.filter(Indicator.provider == filters[k])

            elif k == 'asn':
                s = s.filter(Indicator.asn == filters[k])

            elif k == 'asn_desc':
                s = s.filter(Indicator.asn_desc.like('%{}%'.format(filters[k])))

            elif k == 'cc':
                s = s.filter(Indicator.cc == filters[k])

            elif k == 'rdata':
                s = s.filter(Indicator.rdata == filters[k])

            elif k == 'region':
                s = s.filter(Indicator.region == filters[k])

            else:
                raise InvalidSearch('invalid filter: %s' % k)

        return s

    def _filter_groups(self, token, s):
        groups = token.get('groups', 'everyone')
        if isinstance(groups, str):
            groups = [groups]

        s = s.filter(or_(Indicator.group == g for g in groups))
        return s

    def _search(self, filters, token):
        logger.debug('running search')

        myfilters = dict(filters.items())

        s = self.handle().query(Indicator)

        # group support

        s = self._filter_indicator(myfilters, s)
        s = self._filter_terms(myfilters, s)
        s = self._filter_groups(token, s)
        return s

    def search(self, token, filters, limit=500):
        s = self._search(filters, token)

        limit = filters.pop('limit', limit)

        rv = s.order_by(desc(Indicator.reporttime)).limit(limit)

        start = time.time()
        for i in rv:
            yield self.to_dict(i)

        logger.debug('done: %0.4f' % (time.time() - start))

    def delete(self, token, data=None, id=None):
        if type(data) is not list:
            data = [data]

        ids = []
        for d in data:
            if d.get('id'):
                ids.append(Indicator.id == d['id'])
                logger.debug('removing: %s' % d['id'])
            else:
                ss = self._search(d, token)
                for i in ss:
                    ids.append(Indicator.id == i.id)
                    logger.debug('removing: %s' % i.indicator)

        if len(ids) == 0:
            return 0

        s = self.handle().query(Indicator)
        s = s.filter(or_(*ids))
        rv = s.delete()
        self.handle().commit()

        return rv

    def upsert(self, token, data, **kwargs):
        if type(data) == dict:
            data = [data]

        s = self.handle()

        n = 0
        tmp_added = {}

        for d in data:
            logger.debug(d)

            if not d.get('group'):
                raise InvalidIndicator('missing group')

            if isinstance(d['group'], list):
                d['group'] = d['group'][0]

            # raises AuthError if invalid group
            self._check_token_groups(token, d)

            if PYVERSION == 2:
                if isinstance(d['indicator'], str):
                    d['indicator'] = unicode(d['indicator'])

            self.test_valid_indicator(d)

            tags = d.get("tags", [])
            if len(tags) > 0:
                if isinstance(tags, basestring):
                    tags = tags.split(',')

                del d['tags']

            i = s.query(Indicator).options(lazyload('*')).filter_by(
                provider=d['provider'],
                itype=d['itype'],
                indicator=d['indicator'],
            ).order_by(Indicator.lasttime.desc())

            if d.get('rdata'):
                i = i.filter_by(rdata=d['rdata'])

            if d['itype'] == 'ipv4':
                match = re.search('^(\S+)\/(\d+)$', d['indicator'])  # TODO -- use ipaddress
                if match:
                    i = i.join(Ipv4).filter(Ipv4.ipv4 == match.group(1), Ipv4.mask == match.group(2))
                else:
                    i = i.join(Ipv4).filter(Ipv4.ipv4 == d['indicator'])

            if d['itype'] == 'ipv6':
                match = re.search('^(\S+)\/(\d+)$', d['indicator'])  # TODO -- use ipaddress
                if match:
                    i = i.join(Ipv6).filter(Ipv6.ip == match.group(1), Ipv6.mask == match.group(2))
                else:
                    i = i.join(Ipv6).filter(Ipv6.ip == d['indicator'])

            if d['itype'] == 'fqdn':
                i = i.join(Fqdn).filter(Fqdn.fqdn == d['indicator'])

            if d['itype'] == 'url':
                i = i.join(Url).filter(Url.url == d['indicator'])

            if d['itype'] in HASH_TYPES:
                i = i.join(Hash).filter(Hash.hash == d['indicator'])

            if len(tags):
                i = i.join(Tag).filter(Tag.tag == tags[0])

            r = i.first()

            if r:
                if d.get('lasttime') and arrow.get(d['lasttime']).datetime > arrow.get(r.lasttime).datetime:
                    logger.debug('{} {}'.format(arrow.get(r.lasttime).datetime, arrow.get(d['lasttime']).datetime))
                    logger.debug('upserting: %s' % d['indicator'])

                    r.count += 1
                    r.lasttime = arrow.get(d['lasttime']).datetime.replace(tzinfo=None)

                    if not d.get('reporttime'):
                        d['reporttime'] = arrow.utcnow().datetime

                    r.reporttime = arrow.get(d['reporttime']).datetime.replace(tzinfo=None)

                    if d.get('message'):
                        try:
                            d['message'] = b64decode(d['message'])
                        except Exception as e:
                            pass
                        m = Message(message=d['message'], indicator=r)
                        s.add(m)

                    n += 1
                else:
                    logger.debug('skipping: %s' % d['indicator'])
            else:
                if tmp_added.get(d['indicator']):
                    if d.get('lasttime') in tmp_added[d['indicator']]:
                        logger.debug('skipping: %s' % d['indicator'])
                        continue
                else:
                    tmp_added[d['indicator']] = set()

                if not d.get('lasttime'):
                    d['lasttime'] = arrow.utcnow().datetime.replace(tzinfo=None)

                if not d.get('reporttime'):
                    d['reporttime'] = arrow.utcnow().datetime.replace(tzinfo=None)

                if PYVERSION == 2:
                    d['lasttime'] = arrow.get(d['lasttime']).datetime.replace(tzinfo=None)
                    d['reporttime'] = arrow.get(d['reporttime']).datetime.replace(tzinfo=None)

                if not d.get('firsttime'):
                    d['firsttime'] = d['lasttime']

                ii = Indicator(**d)
                s.add(ii)

                itype = resolve_itype(d['indicator'])

                if itype is 'ipv4':
                    match = re.search('^(\S+)\/(\d+)$', d['indicator'])  # TODO -- use ipaddress
                    if match:
                        ipv4 = Ipv4(ipv4=match.group(1), mask=match.group(2), indicator=ii)
                    else:
                        ipv4 = Ipv4(ipv4=d['indicator'], indicator=ii)

                    s.add(ipv4)

                elif itype is 'ipv6':
                    match = re.search('^(\S+)\/(\d+)$', d['indicator']) # TODO -- use ipaddress
                    if match:
                        ip = Ipv6(ip=match.group(1), mask=match.group(2), indicator=ii)
                    else:
                        ip = Ipv6(ip=d['indicator'], indicator=ii)

                    s.add(ip)

                if itype is 'fqdn':
                    fqdn = Fqdn(fqdn=d['indicator'], indicator=ii)
                    s.add(fqdn)

                if itype is 'url':
                    url = Url(url=d['indicator'], indicator=ii)
                    s.add(url)

                if itype in HASH_TYPES:
                    h = Hash(hash=d['indicator'], indicator=ii)
                    s.add(h)

                for t in tags:
                    t = Tag(tag=t, indicator=ii)
                    s.add(t)

                if d.get('message'):
                    try:
                        d['message'] = b64decode(d['message'])
                    except Exception as e:
                        pass

                    m = Message(message=d['message'], indicator=ii)
                    s.add(m)

                n += 1
                tmp_added[d['indicator']].add(d['lasttime'])

            # if we're in testing mode, this needs re-attaching since we've manipulated the dict for Indicator()
            # see test_store_sqlite
            d['tags'] = ','.join(tags)

        logger.debug('committing')
        start = time.time()
        s.commit()
        logger.debug('done: %0.2f' % (time.time() - start))
        return n
