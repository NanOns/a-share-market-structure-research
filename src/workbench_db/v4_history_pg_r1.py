"""Immutable PG history packs preserving accepted raw/QFQ payload semantics."""
import hashlib
import json
import re
from psycopg.types.json import Jsonb
from .v4_native import connection, create_schema, workspace_schema, configured_dsn
import psycopg

CONTRACT='V4_PG_DATED_HISTORY_INDEX_R1'
DDL='''
CREATE TABLE IF NOT EXISTS history_versions(version text PRIMARY KEY,head_token text NOT NULL,t0 date NOT NULL,source_digest text NOT NULL,logical_digest text NOT NULL,symbol_count bigint NOT NULL,bar_count bigint NOT NULL,created_at timestamptz NOT NULL DEFAULT clock_timestamp());
CREATE TABLE IF NOT EXISTS history(version text NOT NULL REFERENCES history_versions(version) DEFERRABLE INITIALLY DEFERRED,security text NOT NULL,payload jsonb NOT NULL,PRIMARY KEY(version,security));
ALTER TABLE history ALTER CONSTRAINT history_version_fkey DEFERRABLE INITIALLY DEFERRED;
CREATE OR REPLACE FUNCTION reject_history_mutation() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN
 IF TG_OP='INSERT' AND NOT EXISTS(SELECT 1 FROM history_versions WHERE version=NEW.version) THEN RETURN NEW; END IF;
 RAISE EXCEPTION 'IMMUTABLE_HISTORY_VERSION'; END $$;
DROP TRIGGER IF EXISTS immutable_history ON history;
CREATE TRIGGER immutable_history BEFORE INSERT OR UPDATE OR DELETE ON history FOR EACH ROW EXECUTE FUNCTION reject_history_mutation();
DROP TRIGGER IF EXISTS immutable_history_truncate ON history;
CREATE TRIGGER immutable_history_truncate BEFORE TRUNCATE ON history FOR EACH STATEMENT EXECUTE FUNCTION reject_history_mutation();
DROP TRIGGER IF EXISTS immutable_history_version ON history_versions;
CREATE TRIGGER immutable_history_version BEFORE UPDATE OR DELETE ON history_versions FOR EACH ROW EXECUTE FUNCTION reject_history_mutation();
DROP TRIGGER IF EXISTS immutable_history_version_truncate ON history_versions;
CREATE TRIGGER immutable_history_version_truncate BEFORE TRUNCATE ON history_versions FOR EACH STATEMENT EXECUTE FUNCTION reject_history_mutation();
'''

def canonical(value): return json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()

def build(root,rows,*,head_token,t0,source_digest):
    if len(head_token)!=64 or len(source_digest)!=64: raise ValueError('HISTORY_SOURCE_DIGEST_REQUIRED')
    schema=workspace_schema(root,'history')
    with psycopg.connect(configured_dsn(),connect_timeout=5) as pg: create_schema(pg,schema)
    version=hashlib.sha256(canonical(dict(contract_id=CONTRACT,head_token=head_token,t0=t0,source_digest=source_digest))).hexdigest()
    with connection(schema) as pg:
        # Whole frozen history publication writes millions of bars. Bound this
        # producer transaction separately from latency-bounded HTTP reads.
        pg.execute("SET LOCAL statement_timeout = '120s'")
        pg.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))',(schema,))
        pg.execute(DDL)
        existing=pg.execute('SELECT logical_digest,symbol_count,bar_count,head_token,t0::text,source_digest FROM history_versions WHERE version=%s',(version,)).fetchone()
        # Temporary staging remains PG and is transaction-local; no file index.
        pg.execute('CREATE TEMP TABLE stage_history(security text PRIMARY KEY,payload jsonb NOT NULL) ON COMMIT DROP')
        logical=hashlib.sha256();append_digest=logical.update;symbols=bars=0
        for row in rows:
            sid=row['security_id'];series=row['bars']
            if any(b['trade_date']>t0 for b in series): raise ValueError('FUTURE_CHART_BAR')
            dates=[b['trade_date'] for b in series]
            if dates!=sorted(set(dates)): raise ValueError('HISTORY_BAR_ORDER_OR_DUPLICATE')
            pg.execute('INSERT INTO stage_history VALUES(%s,%s)',(sid,Jsonb(series)))
            symbols+=1;bars+=len(series)
        # Canonical order removes source iteration order from version identity.
        with pg.cursor(name='history_digest') as cur:
            cur.execute('SELECT security,payload FROM stage_history ORDER BY security')
            for sid,series in cur: append_digest(canonical(dict(security_id=sid,bars=series))+b'\n')
        digest=logical.hexdigest()
        expected=(digest,symbols,bars,head_token,t0,source_digest)
        if existing and existing!=expected: raise ValueError('HISTORY_VERSION_IDENTITY_CONFLICT')
        if not existing:
            pg.execute('INSERT INTO history SELECT %s,security,payload FROM stage_history',(version,))
            pg.execute('INSERT INTO history_versions VALUES(%s,%s,%s,%s,%s,%s,%s,clock_timestamp())',(version,head_token,t0,source_digest,digest,symbols,bars))
    return dict(contract_id=CONTRACT,engine='postgresql',schema=schema,version=version,head_token=head_token,T0=t0,source_digest=source_digest,logical_digest=digest,symbol_count=symbols,bar_count=bars,price_basis='ACCEPTED_RAW_AND_QFQ_UNCHANGED')

def read(root,binding,day,sid):
    if binding.get('contract_id')=='V4_PG_DATED_HISTORY_QFQ_CORRECTIONS_R2':
        from .v4_history_corrections_pg_v2 import read as corrected_read
        return corrected_read(root,binding,day,sid)
    if binding.get('contract_id')!=CONTRACT or binding.get('engine')!='postgresql': raise ValueError('PG_HISTORY_BINDING_REQUIRED_NO_FALLBACK')
    schema=binding.get('schema')
    if not isinstance(schema,str) or not re.fullmatch(r'v4_history_[a-f0-9]{16}',schema) or binding.get('T0')!=day: raise ValueError('PG_HISTORY_CONTEXT_MISMATCH')
    with connection(schema,read_only=True) as pg:
        version=pg.execute('SELECT head_token,t0::text,source_digest,logical_digest,symbol_count,bar_count FROM history_versions WHERE version=%s',(binding['version'],)).fetchone()
        if version!=(binding['head_token'],day,binding['source_digest'],binding['logical_digest'],binding['symbol_count'],binding['bar_count']): raise ValueError('PG_HISTORY_IDENTITY_MISMATCH')
        row=pg.execute('SELECT payload FROM history WHERE version=%s AND security=%s',(binding['version'],sid)).fetchone()
    return row[0] if row else None
