from elasticsearch_dsl import DocType, String, Date, Integer, Boolean, Float, Ip, GeoPoint, Keyword, Index
from elasticsearch_dsl.connections import connections
import time
import os
### If you need to restore the tokens index to the previous schema run the following from a python interactive shell:
### from reindex_tokens import *
### restore_tokens()

INDEX_NAME = 'tokens'
BACKUP_INDEX_NAME = 'tokens_backup'
ES_NODES = os.getenv('CIF_ES_NODES', '127.0.0.1:9200')
connections.create_connection(hosts=ES_NODES)


class TokenBackup(DocType):
    username = Keyword()
    token = Keyword()
    expires = Date()
    read = Boolean()
    write = Boolean()
    revoked = Boolean()
    acl = Keyword()
    groups = Keyword()
    admin = Boolean()
    last_activity_at = Date()

    class Meta:
        index = BACKUP_INDEX_NAME


class Token(DocType):
    username = Keyword()
    token = Keyword()
    expires = Date()
    read = Boolean()
    write = Boolean()
    revoked = Boolean()
    acl = Keyword()
    groups = Keyword()
    admin = Boolean()
    last_activity_at = Date()

    class Meta:
        index = INDEX_NAME


def reindex_tokens():
    TokenBackup.init()
    connections.create_connection(hosts=ES_NODES)
    backup_results = connections.get_connection().reindex(body={"source": {"index": INDEX_NAME}, "dest": {"index": BACKUP_INDEX_NAME}}, request_timeout=3600)
    if backup_results.get('created') + backup_results.get('updated') == backup_results.get('total'):
        Index(INDEX_NAME).delete()
    else:
        return ('Tokens did not backup properly')
    time.sleep(1)
    Token.init()
    reindex_results = connections.get_connection().reindex(body={"source": {"index": BACKUP_INDEX_NAME}, "dest": {"index": INDEX_NAME}}, request_timeout=3600)
    if reindex_results.get('created') + reindex_results.get('updated') == reindex_results.get('total'):
        return ('Tokens reindexed successfully!')
    else:
        return ('Tokens did not reindex from backup properly')


def restore_tokens():
    connections.create_connection(hosts=ES_NODES)
    Index(INDEX_NAME).delete()

    class Token(DocType):
        username = String()
        token = String()
        expires = Date()
        read = Boolean()
        write = Boolean()
        revoked = Boolean()
        acl = String()
        groups = String()
        admin = Boolean()
        last_activity_at = Date()

        class Meta:
            index = INDEX_NAME

    Token.init()
    reindex_results = connections.get_connection().reindex(body={"source": {"index": BACKUP_INDEX_NAME}, "dest": {"index": INDEX_NAME}}, request_timeout=3600)
    if reindex_results.get('created') + reindex_results.get('updated') == reindex_results.get('total'):
        return ('Tokens restored to previous schema successfully!')
    else:
        return ('Tokens did not restore from backup properly')


def main():
    results = reindex_tokens()
    if results == 'Tokens reindexed successfully!':
        print("Tokens reindexed successfully!")
    else:
        print("Tokens did not reindex properly")


if __name__ == '__main__':
    main()
