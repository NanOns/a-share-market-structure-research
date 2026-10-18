"""Immutable PG history packs preserving accepted raw/QFQ payload semantics."""
import hashlib
import json
import re
from psycopg.types.json import Jsonb
from .v4_native import connection

CONTRACT='V4_PG_DATED_HISTORY_INDEX_R1'

def valid_history_schema_locator(schema):
    """Accept canonical v4 and frozen legacy locators for map-only reads.

    Legacy names are descriptor provenance only. ``read`` below resolves them
    through ``v4.history_migration_map_r1`` and never connects to that schema.
    """
    return schema=='v4' or (isinstance(schema,str) and re.fullmatch(r'v4_history_[a-f0-9]{16}',schema) is not None)

def _require_fixed_storage(pg):
    expected = {
        'history_versions_r1': 'v4.history_versions_r1',
        'history_bars_r1': 'v4.history_bars_r1',
    }
    actual = dict(pg.execute(
        "SELECT c.relname, n.nspname || '.' || c.relname "
        "FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
        "WHERE n.nspname='v4' AND c.relname = ANY(%s)",
        (list(expected),),
    ).fetchall())
    if actual != expected:
        raise RuntimeError('V4_HISTORY_FIXED_STORAGE_MIGRATION_REQUIRED')
    triggers = set(pg.execute("""
        SELECT t.tgname FROM pg_trigger t
        WHERE t.tgrelid IN ('v4.history_versions_r1'::regclass,'v4.history_bars_r1'::regclass)
          AND NOT t.tgisinternal AND t.tgenabled='O'
    """).fetchall())
    required = {
        ('immutable_history_r1',), ('immutable_history_r1_truncate',),
        ('immutable_history_r1_version',), ('immutable_history_r1_version_truncate',),
    }
    if not required.issubset(triggers):
        raise RuntimeError('V4_HISTORY_IMMUTABILITY_MIGRATION_REQUIRED')

def canonical(value): return json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()

def build(root,rows,*,head_token,t0,source_digest):
    if len(head_token)!=64 or len(source_digest)!=64: raise ValueError('HISTORY_SOURCE_DIGEST_REQUIRED')
    version=hashlib.sha256(canonical(dict(contract_id=CONTRACT,head_token=head_token,t0=t0,source_digest=source_digest))).hexdigest()
    with connection('v4') as pg:
        _require_fixed_storage(pg)
        # Whole frozen history publication writes millions of bars. Bound this
        # producer transaction separately from latency-bounded HTTP reads.
        pg.execute("SET LOCAL statement_timeout = '120s'")
        pg.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))',('v4.history_versions_r1',))
        existing=pg.execute('SELECT logical_digest,symbol_count,bar_count,head_token,t0::text,source_digest FROM history_versions_r1 WHERE version=%s',(version,)).fetchone()
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
            pg.execute('INSERT INTO history_bars_r1 SELECT %s,security,payload FROM stage_history',(version,))
            pg.execute('INSERT INTO history_versions_r1 VALUES(%s,%s,%s,%s,%s,%s,%s,clock_timestamp())',(version,head_token,t0,source_digest,digest,symbols,bars))
    return dict(contract_id=CONTRACT,engine='postgresql',schema='v4',version=version,head_token=head_token,T0=t0,source_digest=source_digest,logical_digest=digest,symbol_count=symbols,bar_count=bars,price_basis='ACCEPTED_RAW_AND_QFQ_UNCHANGED')

def read(root,binding,day,sid):
    if binding.get('contract_id')=='V4_PG_DATED_HISTORY_QFQ_CORRECTIONS_R2':
        from .v4_history_corrections_pg_v2 import read as corrected_read
        return corrected_read(root,binding,day,sid)
    if binding.get('contract_id')!=CONTRACT or binding.get('engine')!='postgresql': raise ValueError('PG_HISTORY_BINDING_REQUIRED_NO_FALLBACK')
    schema=binding.get('schema')
    if (not isinstance(schema,str) or binding.get('T0')!=day
            or (schema!='v4' and not re.fullmatch(r'v4_history_[a-f0-9]{16}',schema))):
        raise ValueError('PG_HISTORY_CONTEXT_MISMATCH')
    with connection('v4',read_only=True) as pg:
        if schema!='v4':
            mapped=pg.execute('''SELECT canonical_version,T0::text,head_token,source_digest,logical_digest,symbol_count,bar_count
                FROM history_migration_map_r1 WHERE source_schema=%s AND source_version=%s''',
                (schema,binding['version'])).fetchone()
            expected=(binding['version'],day,binding['head_token'],binding['source_digest'],binding['logical_digest'],binding['symbol_count'],binding['bar_count'])
            if mapped!=expected:raise ValueError('PG_HISTORY_LEGACY_VERSION_NOT_MIGRATED')
        version=pg.execute('SELECT head_token,t0::text,source_digest,logical_digest,symbol_count,bar_count FROM history_versions_r1 WHERE version=%s',(binding['version'],)).fetchone()
        if version!=(binding['head_token'],day,binding['source_digest'],binding['logical_digest'],binding['symbol_count'],binding['bar_count']): raise ValueError('PG_HISTORY_IDENTITY_MISMATCH')
        row=pg.execute('SELECT payload FROM history_bars_r1 WHERE version=%s AND security=%s',(binding['version'],sid)).fetchone()
    return row[0] if row else None
