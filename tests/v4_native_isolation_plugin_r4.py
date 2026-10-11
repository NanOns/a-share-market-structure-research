"""Small R4 isolation profile; refusal cannot satisfy business exceptions."""
import json
import os
from pathlib import Path
import traceback
import re
import hashlib
import pytest

class V4DatabaseGuardViolation(BaseException): pass
ACTIVE=None
EVENTS=[]

@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_protocol(item,nextitem):
    global ACTIVE
    ACTIVE=item.nodeid
    try: yield
    finally: ACTIVE=None

def pytest_configure(config):
    import psycopg
    from psycopg.conninfo import conninfo_to_dict
    expected=conninfo_to_dict(os.environ['V4_NATIVE_PG_DSN'])
    original=psycopg.connect
    allowed_identities={tuple(expected[k] for k in ('host','port','dbname','user'))}
    fixture_clusters={}
    capability=os.environ.get('R4_PG_TEST_CAPABILITIES')
    if capability:
        path=Path(capability).resolve()
        if not path.is_relative_to(Path(__file__).resolve().parents[1]/'docs/audits/full_system_r4_pg_only_20261011_fbd23a6b'):raise V4DatabaseGuardViolation('R4_CAPABILITY_MANIFEST_OUTSIDE_AUDIT')
        manifest=json.loads(path.read_bytes())
        if manifest.get('contract_id')!='R4_ISOLATED_PG_TEST_CAPABILITIES_R1':raise V4DatabaseGuardViolation('R4_CAPABILITY_CONTRACT_REQUIRED')
        for item in manifest['databases']:
            if item['purpose']!='FEP_ENGINEERING_FIXTURE_R1' or item['database'] not in ('fep_e1_fresh','fep_e1_upgrade'):raise V4DatabaseGuardViolation('R4_CAPABILITY_SCOPE_ESCAPE')
            if item['port'] not in ('55792','55793'):raise V4DatabaseGuardViolation('R4_CAPABILITY_PORT_SCOPE_ESCAPE')
            dsn=dict(expected,dbname=item['database'],port=item['port'])
            with original(**dsn) as pg:
                actual=Path(pg.execute('SHOW data_directory').fetchone()[0]).resolve()
                if actual!=Path(item['data_directory']).resolve() or not actual.is_relative_to(Path('G:/codex_tmp/full_system_r4_fbd23a6b').resolve()):raise V4DatabaseGuardViolation('R4_CAPABILITY_CLUSTER_IDENTITY_MISMATCH')
                if pg.execute('SELECT count(*) FROM r4_evidence.migrations').fetchone()[0]!=33:raise V4DatabaseGuardViolation('R4_CAPABILITY_001_033_REQUIRED')
            allowed_identities.add(tuple(dsn[k] for k in ('host','port','dbname','user')))
            fixture_clusters[(dsn['host'],dsn['port'],dsn['user'])]=(item['database'],actual)
    with original(os.environ['V4_NATIVE_PG_DSN']) as pg:
        actual=Path(pg.execute('SHOW data_directory').fetchone()[0]).resolve()
        if actual!=Path(os.environ['R4_PG_DATA_DIRECTORY']).resolve() or not actual.is_relative_to(Path('G:/codex_tmp').resolve()): raise V4DatabaseGuardViolation('R4_ISOLATED_PG_IDENTITY_MISMATCH')
    patch=pytest.MonkeyPatch();config._r4_patch=patch
    def guarded_pg(conninfo='',**kwargs):
        parsed=conninfo_to_dict(conninfo,**{k:kwargs[k] for k in ('host','port','dbname','user') if k in kwargs})
        decision='ALLOW' if tuple(parsed.get(k) for k in ('host','port','dbname','user')) in allowed_identities else 'REJECT'
        cluster=fixture_clusters.get(tuple(parsed.get(k) for k in ('host','port','user')))
        if decision=='REJECT' and cluster and ACTIVE and ACTIVE.endswith('test_E1_24_concurrent_cas_and_same_request'):
            base,directory=cluster;database=parsed.get('dbname','')
            if database=='postgres' or re.fullmatch(re.escape(base)+r'_concurrency_[0-9a-f]{8}',database):
                with original(conninfo) as witness:
                    if Path(witness.execute('SHOW data_directory').fetchone()[0]).resolve()!=directory:raise V4DatabaseGuardViolation('R4_DYNAMIC_FIXTURE_DIRECTORY_MISMATCH')
                    if database!='postgres' and witness.execute('SELECT count(*) FROM r4_evidence.migrations').fetchone()[0]!=33:raise V4DatabaseGuardViolation('R4_DYNAMIC_FIXTURE_SQL_IDENTITY_REQUIRED')
                decision='ALLOW'
        EVENTS.append(dict(nodeid=ACTIVE,engine='postgresql',decision=decision,stack=traceback.format_stack(limit=8)))
        if decision=='REJECT': raise V4DatabaseGuardViolation('R4_UNATTESTED_PG_FORBIDDEN')
        return original(conninfo,**kwargs)
    patch.setattr(psycopg,'connect',guarded_pg)
    def sql_audit(original):
        def call(owner,query,*args,**kwargs):
            pg=owner if isinstance(owner,psycopg.Connection) else owner.connection
            text=query if isinstance(query,str) else query.as_string(pg) if hasattr(query,'as_string') else '<BINARY_SQL>'
            operation=text.lstrip().split(None,1)[0].upper() if text.strip() else 'EMPTY'
            EVENTS.append(dict(event='SQL_INTENT',nodeid=ACTIVE,engine='postgresql',database=pg.info.dbname,user=pg.info.user,host=pg.info.host,port=pg.info.port,operation=operation,read_write='READ' if operation in ('SELECT','SHOW','EXPLAIN') else 'WRITE_OR_CONTROL',relations=re.findall(r'\b(?:FROM|JOIN|INTO|UPDATE|TABLE)\s+([a-zA-Z_][a-zA-Z0-9_.]*)',text,re.I)[:12],query_sha256=hashlib.sha256(text.encode()).hexdigest(),parameters_persisted=False))
            return original(owner,query,*args,**kwargs)
        return call
    for owner,method in ((psycopg.Connection,'execute'),(psycopg.Cursor,'execute'),(psycopg.Cursor,'executemany'),(psycopg.ServerCursor,'execute')):
        patch.setattr(owner,method,sql_audit(getattr(owner,method)))
    def reject(engine):
        def call(*args,**kwargs):
            EVENTS.append(dict(nodeid=ACTIVE,engine=engine,decision='REJECT',stack=traceback.format_stack(limit=8)))
            raise V4DatabaseGuardViolation('R4_NON_POSTGRES_FORBIDDEN:'+engine)
        return call
    import sqlite3
    patch.setattr(sqlite3,'connect',reject('sqlite3'))
    try: import duckdb
    except ImportError: pass
    else: patch.setattr(duckdb,'connect',reject('duckdb'))

def pytest_sessionfinish(session,exitstatus):
    p=Path(os.environ['R4_CONNECTION_LEDGER']);p.parent.mkdir(parents=True,exist_ok=True)
    tmp=p.with_suffix('.tmp');tmp.write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in EVENTS),encoding='utf8');os.replace(tmp,p)

def pytest_unconfigure(config):
    if hasattr(config,'_r4_patch'): config._r4_patch.undo()
