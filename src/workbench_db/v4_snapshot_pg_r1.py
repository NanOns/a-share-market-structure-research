"""Native PG immutable research schemas; descriptor is an audit binding only."""
from contextlib import contextmanager
import hashlib
import json
import re
import psycopg
from psycopg import sql
from .v4_native import configured_dsn, connection

CONTRACT='V4_PG_RESEARCH_SNAPSHOT_R1'

def translate(query):
    # Only the explicit frozen research SQL surface is accepted here.
    query=re.sub(r"json_extract\(payload,'\$\.([a-zA-Z0-9_.]+)'\)",lambda m:"(payload::jsonb #>> '{"+m.group(1).replace('.',',')+"}')",query)
    ignore=query.startswith('INSERT OR IGNORE ')
    if ignore: query=query.replace('INSERT OR IGNORE ','INSERT ',1)+' ON CONFLICT DO NOTHING'
    return query.replace('?', '%s')

class Builder:
    def __init__(self,root,release_id):
        if not isinstance(release_id,str) or not re.fullmatch(r'[a-f0-9]{24,64}',release_id):
            raise ValueError('PG_RESEARCH_RELEASE_ID_INVALID')
        self.schema='v4';self.release_id=release_id
        self.pg=psycopg.connect(configured_dsn(),connect_timeout=5)
        self.pg.execute('SET search_path TO pg_temp,v4,pg_catalog')
        self.pg.execute("SET statement_timeout='180s'")
        self.pg.execute("SET lock_timeout='5s'")
    def execute(self,query,params=()): return self.pg.execute(translate(query),params)
    def executescript(self,query):
        query=re.sub(r'(?i)\bCREATE\s+TABLE\s+(?!IF\s+NOT\s+EXISTS)([a-z_][a-z0-9_]*)',r'CREATE TEMP TABLE \1',query)
        query=re.sub(r'(?i)\bCREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+([a-z_][a-z0-9_]*)',r'CREATE TEMP TABLE IF NOT EXISTS \1',query)
        return self.pg.execute(query)
    def executemany(self,query,rows):
        with self.pg.cursor() as cur: cur.executemany(translate(query),rows)
    def seal(self,meta):
        return self.seal_release(meta,storage_kind='snapshot',source_binding=dict(kind='LEGACY_R1_METADATA',manifest_sha256=hashlib.sha256(json.dumps(meta,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()))
    def seal_release(self,meta,*,storage_kind,source_binding,consumer_binding=None):
        from .v4_snapshot_pg_r2 import DIGEST_CONTRACT, EXTRA_FIELDS, database_identity
        from .v4_research_release_pg_r1 import TABLE_RELATIONS, _central_table_manifest, canonical, digest
        consumer_binding=consumer_binding or {}
        if meta.get('release_id')!=self.release_id:raise ValueError('PG_RESEARCH_RELEASE_ID_MISMATCH')
        t0=meta.get('context',{}).get('accepted_trade_date')
        if not t0:raise ValueError('PG_RESEARCH_T0_REQUIRED')
        required={'snapshot':{'objects','aliases','members','metadata'},
                  'series':{'objects','aliases','members','metadata','bars'},
                  'journal':{'objects','aliases','members','metadata','days','day_inputs'}}
        if storage_kind not in required or set(consumer_binding)!=EXTRA_FIELDS[storage_kind]:
            raise ValueError('PG_RESEARCH_STORAGE_CONTRACT_REQUIRED')
        staged={row[0] for row in self.pg.execute("SELECT relname FROM pg_class WHERE relnamespace=pg_my_temp_schema() AND relkind='r'")}
        if staged!=required[storage_kind]:raise ValueError('PG_RESEARCH_STAGING_TABLE_SET_MISMATCH')
        if storage_kind=='snapshot' and self.pg.execute("SELECT value FROM metadata WHERE key='snapshot'").fetchone() is None:
            raise ValueError('PG_RESEARCH_SNAPSHOT_METADATA_REQUIRED')
        if self.pg.execute('SELECT 1 FROM v4.research_releases WHERE release_id=%s',(self.release_id,)).fetchone():
            raise ValueError('PG_RESEARCH_RELEASE_ID_CONFLICT')
        meta_manifest=dict(contract_id=DIGEST_CONTRACT,storage_kind=storage_kind,metadata=meta,
                           metadata_sha256=digest(meta),source_binding=source_binding)
        descriptor=dict(contract_id='V4_PG_RESEARCH_SNAPSHOT_R3_SINGLE_SCHEMA',engine='postgresql',
            schema='v4',release_id=self.release_id,T0=t0,content_manifest=None,
            database_identity=database_identity(self.pg))
        # The descriptor and release row are completed in one transaction after
        # every staged table has been inserted and independently hashed.
        self.pg.execute('INSERT INTO v4.research_releases(release_id,storage_kind,contract_id,t0,canonical_manifest,sealed) VALUES(%s,%s,%s,%s,%s::jsonb,false)',
            (self.release_id,storage_kind,descriptor['contract_id'],t0,json.dumps({'migration_contract_id':'V4_SINGLE_SCHEMA_RESEARCH_STORAGE_R1'},separators=(',',':'))))
        for source_table,(relation,columns) in TABLE_RELATIONS.items():
            if source_table not in required[storage_kind]:continue
            col_sql=sql.SQL(',').join(map(sql.Identifier,columns))
            extra=[]
            if source_table in {'days','day_inputs'}:extra=[sql.SQL('{}::date').format(sql.Identifier('day')) if column=='day' else sql.Identifier(column) for column in columns]
            source_cols=sql.SQL(',').join(extra) if extra else col_sql
            self.pg.execute(sql.SQL('INSERT INTO v4.{}(release_id,{}) SELECT %s,{} FROM pg_temp.{}').format(
                sql.Identifier(relation),col_sql,source_cols,sql.Identifier(source_table)),(self.release_id,))
        central=_central_table_manifest(self.pg,self.release_id,storage_kind)
        from .v4_snapshot_pg_r2 import TABLES,EXTRA_TABLES
        definitions={name:tuple((column,'text') for column in cols) for name,cols in TABLES.items()}
        definitions.update(EXTRA_TABLES[storage_kind])
        meta_manifest['tables']={name:dict(columns=[column for column,_ in definitions[name]],types=[kind for _,kind in definitions[name]],**central[name]) for name in sorted(required[storage_kind])}
        if storage_kind=='series':
            bind=consumer_binding
            self.pg.execute('INSERT INTO v4.research_series_versions(release_id,series_contract_id,source_digest,bar_count,symbol_count,price_basis) VALUES(%s,%s,%s,%s,%s,%s)',
                (self.release_id,bind['series_contract_id'],bind['source_digest'],bind['bar_count'],bind['symbol_count'],meta.get('price_basis','RAW_OR_CONTRACT_BOUND')))
        elif storage_kind=='journal':
            bind=consumer_binding;head=bind['head']
            if isinstance(head,str):head=json.loads(head)
            self.pg.execute('INSERT INTO v4.research_journal_versions(release_id,journal_contract,head,registry_schema,registry_key) VALUES(%s,%s,%s::jsonb,%s,%s)',
                (self.release_id,bind['journal_contract'],json.dumps(head,ensure_ascii=False,separators=(',',':')),bind['registry_schema'],bind['registry_key']))
        descriptor['content_manifest']=meta_manifest
        descriptor.update(consumer_binding)
        descriptor['logical_digest']=digest(descriptor)
        self.pg.execute('UPDATE v4.research_releases SET canonical_manifest=%s::jsonb,sealed=true WHERE release_id=%s',
            (json.dumps(meta_manifest,ensure_ascii=False,separators=(',',':')),self.release_id))
        return descriptor
    def commit(self): self.pg.commit()
    def close(self): self.pg.close()

class ReadTransaction:
    def __init__(self,pg): self.pg=pg
    def execute(self,query,params=()): return self.pg.execute(translate(query),params)

@contextmanager
def read(descriptor):
    if descriptor.get('contract_id') in ('V4_PG_RESEARCH_SNAPSHOT_R2','V4_PG_RESEARCH_SNAPSHOT_R3_SINGLE_SCHEMA'):
        from .v4_snapshot_pg_r2 import read as read_r2
        with read_r2(descriptor) as reader:
            yield reader
        return
    if descriptor.get('contract_id')!=CONTRACT or descriptor.get('engine')!='postgresql': raise ValueError('PG_SNAPSHOT_BINDING_REQUIRED_NO_FALLBACK')
    with connection(descriptor['schema'],read_only=True) as pg:
        identity=pg.execute('SELECT digest,contract_id FROM snapshot_identity').fetchall()
        if identity!=[(descriptor['logical_digest'],CONTRACT)]: raise ValueError('PG_SNAPSHOT_IDENTITY_MISMATCH')
        yield ReadTransaction(pg)
