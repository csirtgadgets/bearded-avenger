from elasticsearch_dsl import DocType, Text, Date, Integer, Float, Ip, Text, Keyword, \
      GeoPoint, analyzer, tokenizer
from elasticsearch_dsl.field import Field


class IpRange(Field):
    # canonical in elasticsearch_dsl >6.x, doesn't support CIDRs until ES 6.1
    # if elasticsearch_dsl/ES updated past those versions, this class should be removed
    name = 'ip_range'

class Indicator(DocType):
    ssdeep_tokenizer = tokenizer('ssdeep_tokenizer', type='ngram', min_gram=7, max_gram=7)
    ssdeep_analyzer = analyzer('ssdeep_analyzer', tokenizer=ssdeep_tokenizer)
    indicator = Keyword()
    indicator_ipv4 = Ip()
    indicator_ipv4_mask = Integer()
    indicator_iprange = IpRange() # works for both IPv4 and v6
    indicator_ipv6 = Keyword()
    indicator_ipv6_mask = Integer()
    indicator_ssdeep_chunksize = Integer()
    indicator_ssdeep_chunk = Text(analyzer=ssdeep_analyzer)
    indicator_ssdeep_double_chunk = Text(analyzer=ssdeep_analyzer)
    group = Keyword()
    itype = Keyword()
    tlp = Keyword()
    provider = Keyword()
    portlist = Text()
    asn = Float()
    asn_desc = Text()
    cc = Text(fields={'raw': Keyword()})
    protocol = Text(fields={'raw': Keyword()})
    reporttime = Date()
    lasttime = Date()
    firsttime = Date()
    confidence = Float()
    timezone = Text()
    city = Text(fields={'raw': Keyword()})
    description = Keyword()
    tags = Keyword(multi=True, fields={'raw': Keyword()})
    rdata = Keyword()
    count = Integer()
    message = Text(multi=True)
    location = GeoPoint()
