
try:
    from rdflib import Graph, ConjunctiveGraph, Literal, URIRef, RDF
except ImportError as e:
    print(e)
    raise SystemExit('Requires RDFLib to be installed')

from cif.store import Store
import logging
from pprint import pprint
import uuid
import os
import binascii

from cif.constants import TOKEN_LENGTH


class Rdflib(Store):

    name = 'rdflib'

    def __init__(self, logger=logging.getLogger(__name__), *args, **kwargs):

        self.logger = logger
        self._open_store()
        self.store_id = Literal(str(uuid.uuid4()))

    def _open_store(self, store='IOMemory'):
        self.logger.debug("opening store...")
        self.handle = ConjunctiveGraph(store, identifier="permanent")

    def _close_store(self):
        self.logger.debug("closing store")
        self.handle.close(commit_pending_transaction=True)

    def indicators_search(self, token, data):
        rv = []
        for s, p, o in self.handle.triples((Literal(data['indicator']), None, None)):
            rv.append((s, p, o))

        return rv

    # http://en.wikipedia.org/wiki/Resource_Description_Framework
    def indicators_create(self, token, data):
        if type(data) is not list:
            data = [data]

        for d in data:
            subject = Literal(d["indicator"])

            for k in d:
                if k == "indicator":
                    self.handle.add((subject, RDF.type, Literal(d["itype"]), self.store_id))
                else:
                    subject = Literal(d["indicator"])
                    self.handle.add((subject, Literal(k), Literal(d[k]), self.store_id))

        self.logger.debug(self.handle.serialize(format="trig"))

        return len(data)

    def ping(self, token):
        return True

    def _token_generate(self):
        return binascii.b2a_hex(os.urandom(TOKEN_LENGTH))

    def tokens_admin_exists(self):
        return True

    def tokens_create(self, data):
        return True

    def tokens_delete(self, data):
        return True

    def tokens_search(self, data):
        return True

    def token_admin(self, token):
        return True

    def token_read(self, token):
        return True

    def token_write(self, token):
        return True

    def token_edit(self, data):
        return True

    def token_last_activity_at(self, token, timestamp=None):
        return True

Plugin = Rdflib