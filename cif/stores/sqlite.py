import sqlite3

from cif.stores import Store


class Plugin(Store):

    name = 'sqlite'

    def __init__(self, dbfile=":memory", autocommit=True, dictrows=True):
        self.dbfile = dbfile
        self.autocommit = autocommit
        self.dictrows = dictrows