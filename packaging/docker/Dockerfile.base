FROM python:2.7.10
MAINTAINER Wes Young (wes@csirtgadgets.org)

ENV NEWUSER cif
RUN useradd -m $NEWUSER

RUN pip install pyzmq --install-option="--zmq=bundled"
RUN pip install git+https://github.com/csirtgadgets/py-whiteface-sdk.git
RUN pip install git+https://github.com/csirtgadgets/bearded-avenger.git

VOLUME /var/lib

RUN for path in \
    /var/lib/cif/cache \
    /var/lib/cif/rules \
    /var/log/cif \
    ; do \
        mkdir -p $path; \
        chown cif:cif "$path"; \
    done

VOLUME /var/log/cif
VOLUME /var/lib/cif/rules
VOLUME /var/lib/cif/cache

COPY supervisord.conf /etc/supervisord.conf

EXPOSE 5000

CMD ["supervisord", "-c", "/etc/supervisord.conf"]
