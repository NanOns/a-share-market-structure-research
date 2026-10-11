"""Native PG immutable research schemas; descriptor is an audit binding only."""
from contextlib import contextmanager
import hashlib
import json
import re
import psycopg
from psycopg import sql
from .v4_native import configured_dsn, connection, create_schema

CONTRACT='V4_PG_RESEARCH_SNAPSHOT_R1'

def translate(query):
    # Only the explicit frozen research SQL surface is accepted here.
    query=re.sub(r"json_extract\(payload,'\$\.([a-zA-Z0-9_.]+)'\)",lambda m:"(payload::jsonb #>> '{"+m.group(1).replace('.',',')+"}')",query)
    ignore=query.startswith('INSERT OR IGNORE ')
    if ignore: query=query.replace('INSERT OR IGNORE ','INSERT ',1)+' ON CONFLICT DO NOTHING'
    return query.replace('?', '%s')

class Builder:
    def __init__(self,root,release_id):
        self.schema='v4_research_'+hashlib.sha256((str(root).casefold()+':'+release_id).encode()).hexdigest()[:24]
        self.pg=psycopg.connect(configured_dsn(),connect_timeout=5)
        create_schema(self.pg,self.schema)
        self.pg.execute(sql.SQL('SET LOCAL search_path TO {},pg_catalog').format(sql.Identifier(self.schema)))
        self.pg.execute("SET LOCAL statement_timeout='30s'")
        self.pg.execute("SET LOCAL lock_timeout='5s'")
    def execute(self,query,params=()): return self.pg.execute(translate(query),params)
    def executescript(self,query): return self.pg.execute(query)
    def executemany(self,query,rows):
        with self.pg.cursor() as cur: cur.executemany(translate(query),rows)
    def seal(self,meta):
        sha=hashlib.sha256(json.dumps(meta,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
        self.pg.execute('CREATE TABLE snapshot_identity(digest text PRIMARY KEY,contract_id text NOT NULL)')
        self.pg.execute('INSERT INTO snapshot_identity VALUES(%s,%s)',(sha,CONTRACT))
        self.pg.execute("CREATE FUNCTION reject_snapshot_mutation() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'IMMUTABLE_RESEARCH_SNAPSHOT'; END $$")
        for table in ('objects','aliases','members','metadata','snapshot_identity'):
            self.pg.execute(sql.SQL('CREATE TRIGGER immutable_snapshot BEFORE INSERT OR UPDATE OR DELETE OR TRUNCATE ON {} FOR EACH STATEMENT EXECUTE FUNCTION reject_snapshot_mutation()').format(sql.Identifier(table)))
        return dict(contract_id=CONTRACT,engine='postgresql',schema=self.schema,logical_digest=sha,release_id=meta['release_id'],T0=meta['context']['accepted_trade_date'])
    def commit(self): self.pg.commit()
    def close(self): self.pg.close()

class ReadTransaction:
    def __init__(self,pg): self.pg=pg
    def execute(self,query,params=()): return self.pg.execute(translate(query),params)

@contextmanager
def read(descriptor):
    if descriptor.get('contract_id') == 'V4_PG_RESEARCH_SNAPSHOT_R2':
        from .v4_snapshot_pg_r2 import read as read_r2
        with read_r2(descriptor) as reader:
            yield reader
        return
    if descriptor.get('contract_id')!=CONTRACT or descriptor.get('engine')!='postgresql': raise ValueError('PG_SNAPSHOT_BINDING_REQUIRED_NO_FALLBACK')
    with connection(descriptor['schema'],read_only=True) as pg:
        identity=pg.execute('SELECT digest,contract_id FROM snapshot_identity').fetchall()
        if identity!=[(descriptor['logical_digest'],CONTRACT)]: raise ValueError('PG_SNAPSHOT_IDENTITY_MISMATCH')
        yield ReadTransaction(pg)
