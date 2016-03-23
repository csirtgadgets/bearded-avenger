# -*- coding: latin-1 -*-
import pytest

from pprint import pprint
from cif.smrt.parser.znltk import Nltk_
import arrow

vnc = """
701          |  UUNET - MCI Communications Ser  |      68.135.40.6  |  2015-12-07 17:42:20  |  vncprobe
701          |  UUNET - MCI Communications Ser  |   71.178.253.108  |  2015-12-07 17:26:28  |  vncprobe
760          |  University of Vienna, Austria,  |   131.130.69.196  |  2015-12-08 07:25:40  |  vncprobe
3215         |  AS3215 Orange S.A.,FR           |     80.13.221.76  |  2015-12-08 10:36:56  |  vncprobe
3462         |  HINET Data Communication Busin  |     114.32.32.66  |  2015-12-03 04:02:22  |  vncprobe
3790         |  RADIOGRAFICA COSTARRICENSE,CR   |     190.10.8.226  |  2015-12-06 19:38:31  |  vncprobe
3790         |  RADIOGRAFICA COSTARRICENSE,CR   |     190.10.9.246  |  2015-12-06 21:09:17  |  vncprobe
"""

ssh = """
701          |  UUNET - MCI Communications Ser  |   96.242.156.153  |  2016-03-17 11:02:29  |  sshpwauth
701          |  UUNET - MCI Communications Ser  |    96.238.182.78  |  2016-03-19 06:39:01  |  sshpwauth
1241         |  FORTHNET-GR Forthnet,GR         |   194.219.11.212  |  2016-03-21 14:41:28  |  sshpwauth
1680         |  NV-ASN 013 NetVision Ltd.,IL    |  212.150.196.217  |  2016-03-22 12:49:34  |  sshpwauth
1916         |  Associação Rede Nacional de   |  200.133.218.149  |  2016-03-20 21:45:48  |  sshpwauth
2497         |  IIJ Internet Initiative Japan   |  202.232.254.106  |  2016-03-22 03:22:00  |  sshpwauth
2516         |  KDDI KDDI CORPORATION,JP        |   106.187.48.176  |  2016-03-22 08:53:34  |  sshpwauth
2516         |  KDDI KDDI CORPORATION,JP        |   106.185.34.252  |  2016-03-22 08:25:34  |  sshpwauth
2856         |  BT-UK-AS British Telecommunica  |     109.157.5.97  |  2016-03-18 06:17:30  |  sshpwauth
2860         |  NOS_COMUNICACOES NOS COMUNICAC  |      83.132.9.42  |  2016-03-22 06:19:56  |  sshpwauth
"""

@pytest.mark.xfail
def test_nltk_vnc():
    n = Nltk_(None, None, None, None)
    x = n.process(None, None, vnc)

    ips = set()
    ts = set()
    tags = set()

    for i in x:
        ips.add(i.indicator)
        ts.add(i.lasttime)
        tags.add(i.tags[0])

    assert '190.10.9.246' in ips
    assert '68.135.40.6' in ips
    assert '114.32.32.66' in ips
    assert '80.13.221.76' in ips

    assert 'vncprobe' in tags
    assert arrow.get('2015-12-06T21:09:17.000000Z').datetime in ts

@pytest.mark.xfail
def test_nltk_ssh():
    n = Nltk_(None, None, None, None)
    x = n.process(None, None, ssh)

    ips = set()
    ts = set()
    tags = set()

    for i in x:
        ips.add(i.indicator)
        ts.add(i.lasttime)
        tags.add(i.tags[0])

    assert '96.242.156.153' in ips
    assert '83.132.9.42' in ips

    assert 'sshpwauth' in tags
    assert arrow.get('2016-03-22T06:19:56Z').datetime in ts
