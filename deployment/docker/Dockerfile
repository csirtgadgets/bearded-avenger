FROM ubuntu:14.04
MAINTAINER Wes Young <wes@csirtgadgets.org>

ENV CIF_VERSION 3.0.0a16

RUN apt-get update
RUN apt-get install -qq software-properties-common python-software-properties

RUN echo "yes" | add-apt-repository ppa:maxmind/ppa

RUN apt-get update
RUN apt-get install -y python2.7 python-pip python-dev git libffi-dev libssl-dev sqlite3 wget build-essential git \
    python2.7 python-pip python python-dev geoip-bin geoipupdate python-pytest uuid-dev libxml2-dev python-lxml \
    libxslt1-dev zlib1g-dev

RUN pip install 'setuptools>=11.3' 'ansible>=2.1' versioneer markupsafe 'supervisor==3.2.1'


VOLUME /usr/local/share/GeoIP
COPY configs/GeoIP.conf /etc/
RUN geoipupdate -v

RUN adduser --disabled-password --gecos '' cif

WORKDIR /
RUN set -ex \
    && for path in \
        /var/log/cif \
        /var/lib/cif \
        /etc/cif \
    ; do \
        mkdir -p "$path"; \
        chown -R cif:cif "$path"; \
    done

RUN wget https://github.com/csirtgadgets/bearded-avenger/archive/$CIF_VERSION.tar.gz
RUN tar -zxvf $CIF_VERSION.tar.gz
WORKDIR /bearded-avenger-$CIF_VERSION

RUN cp -r rules /etc/cif/
RUN pip install -r dev_requirements.txt
RUN py.test
RUN python setup.py install

COPY configs/cif.conf /
COPY scripts/start.sh /
COPY scripts/cif-entrypoint.sh /

VOLUME /etc/cif
VOLUME /var/log/cif
VOLUME /var/lib/cif

EXPOSE 443 5000
ENTRYPOINT ["/cif-entrypoint.sh"]
CMD ["/bin/bash", "/start.sh"]