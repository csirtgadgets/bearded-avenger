FROM python:2.7.10
MAINTAINER Wes Young (wes@csirtgadgets.org)

ENV NEWUSER cif
RUN useradd -m $NEWUSER

RUN pip install pyzmq --install-option="--zmq=bundled"
RUN pip install git+https://github.com/csirtgadgets/py-whiteface-sdk.git
RUN pip install git+https://github.com/csirtgadgets/bearded-avenger.git

#ADD requirements.txt /src/requirements.txt
#RUN cd /src; pip install -r requirements.txt
#ADD cif /src/cif
#ADD rules /src/rules
#RUN mkdir -p /var/data

COPY supervisord.conf /etc/supervisord.conf

EXPOSE 5000

CMD ["supervisord", "-c", "/etc/supervisord.conf"]
