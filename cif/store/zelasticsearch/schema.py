from elasticsearch_dsl import DocType, String, Date, Integer, Float, Ip, GeoPoint, Byte, MetaField


class Indicator(DocType):
    indicator = String(index="not_analyzed")
    indicator_ipv4 = Ip()
    indicator_ipv6 = String(index='not_analyzed')
    indicator_ipv6_mask = Integer()
    group = String(index="not_analyzed")
    itype = String(index="not_analyzed")
    tlp = String(index="not_analyzed")
    provider = String(index="not_analyzed")
    portlist = String()
    asn = Float()
    asn_desc = String()
    cc = String(fields={'raw': String(index='not_analyzed')})
    protocol = String(fields={'raw': String(index='not_analyzed')})
    reporttime = Date()
    lasttime = Date()
    firsttime = Date()
    confidence = Integer()
    timezone = String()
    city = String(fields={'raw': String(index='not_analyzed')})
    description = String(index="not_analyzed")
    tags = String(multi=True, fields={'raw': String(index='not_analyzed')})
    rdata = String(index="not_analyzed")
    count = Integer()
    message = String(multi=True)

    class Meta:
        timestamp = MetaField(enabled=True)