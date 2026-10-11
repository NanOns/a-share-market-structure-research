"""G-only actual fresh/upgrade SQL and frozen canonical engineering fixtures."""
import argparse
from datetime import datetime,timezone
import gzip
import hashlib
import inspect
import json
import os
from pathlib import Path
import subprocess
import sys
import psycopg
from psycopg import sql

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'src'))
from workbench_analysis.fep_e5 import canonical_ledger as ledger
BASE=Path('G:/codex_tmp/r4_r3_fep_fixtures')
OUT=ROOT/'docs/audits/r4_r3_scope_20261011'
SOURCE=Path('G:/codex work/大A交易')
BIN=Path('E:/Postgres/bin')
DSNS={'fresh':'host=127.0.0.1 port=55794 user=r4_isolated_admin dbname=fep_e5b_fresh',
      'upgrade':'host=127.0.0.1 port=55793 user=r4_isolated_admin dbname=fep_e5b_upgrade'}

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        while b:=f.read(65536):h.update(b)
    return h.hexdigest()

def emit(name,value):
    path=OUT/name;tmp=path.with_suffix('.tmp')
    tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2,default=str)+'\n',encoding='utf8');os.replace(tmp,path)

def admin(port):return f'host=127.0.0.1 port={port} user=r4_isolated_admin dbname=postgres connect_timeout=5'

def cluster(port=55793):
    if port not in (55793,55794):raise ValueError('DEDICATED_FIXTURE_PORT_REQUIRED')
    kind='upgrade' if port==55793 else 'fresh'
    directory=BASE/(kind+'_data')
    BASE.mkdir(parents=True,exist_ok=True)
    if not directory.exists():
        env=dict(os.environ,TMP=str(BASE),TEMP=str(BASE),TMPDIR=str(BASE))
        with (BASE/(kind+'_INITDB_RAW.log')).open('x',encoding='utf8') as log:
            subprocess.run([str(BIN/'initdb.exe'),'-D',str(directory),'-U','r4_isolated_admin','--encoding=UTF8','--locale=C','--auth=trust'],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
    pid=directory/'postmaster.pid'
    if not pid.exists():
        # Windows server children can inherit capture pipes after pg_ctl exits.
        # A file preserves raw startup output without waiting for server EOF.
        with (BASE/'START_RAW.log').open('a',encoding='utf8') as startup:
            subprocess.run([str(BIN/'pg_ctl.exe'),'-D',str(directory),'-l',str(BASE/(kind+'_SERVER.log')),'-o',f'-p {port} -h 127.0.0.1','-w','start'],stdout=startup,stderr=subprocess.STDOUT,check=True,timeout=90)
    with psycopg.connect(admin(port)) as pg:
        if Path(pg.execute('show data_directory').fetchone()[0]).resolve()!=directory.resolve():raise ValueError('ISOLATED_UPGRADE_CLUSTER_IDENTITY_MISMATCH')
        return dict(port=port,data_directory=str(directory),system_identifier=pg.execute('select system_identifier::text from pg_control_system()').fetchone()[0])

def create_database(port,name,template=None):
    with psycopg.connect(admin(port),autocommit=True) as pg:
        if pg.execute('select 1 from pg_database where datname=%s',(name,)).fetchone():return False
        pg.execute(sql.SQL('CREATE DATABASE {}'+(' TEMPLATE {}' if template else '')).format(sql.Identifier(name),*([sql.Identifier(template)] if template else [])))
    return True

def install():
    upgrade=cluster();fresh=cluster(55794);paths=[p.relative_to(ROOT).as_posix() for p in sorted((ROOT/'src/workbench_db/migrations/v4_postgres').glob('*.sql'))]
    receipts={}
    for kind,port in [('fresh',55794),('upgrade',55793)]:
        name='fep_e5b_'+kind;create_database(port,name)
        first=[]
        if kind=='upgrade':
            with psycopg.connect(DSNS[kind],autocommit=True) as core:
                first=ledger.apply(core,ROOT,paths[:27])
            # CREATE DATABASE TEMPLATE requires the template connection closed.
            create_database(port,'fep_e1_core_template',name)
        with psycopg.connect(DSNS[kind],autocommit=True) as pg:
            before=pg.execute("select count(*) from information_schema.tables where table_schema in ('v4','fep')").fetchone()[0]
            if kind=='upgrade':
                middle=ledger.apply(pg,ROOT,paths[27:31])
                predecessor=pg.execute("select table_schema,table_name from information_schema.tables where table_schema in ('v4','fep') order by 1,2").fetchall()
                final=ledger.apply(pg,ROOT,paths[31:])
            else:first=[];middle=[];predecessor=[];final=ledger.apply(pg,ROOT,paths)
            replay=ledger.apply(pg,ROOT,paths)
            if any(r['status']!='ALREADY_APPLIED' for r in replay):raise ValueError('IDEMPOTENT_SQL_REPLAY_FAILED')
            pg.execute('CREATE SCHEMA IF NOT EXISTS r4_evidence');pg.execute('CREATE TABLE IF NOT EXISTS r4_evidence.migrations(path text PRIMARY KEY,sha256 text NOT NULL,applied_at timestamptz NOT NULL DEFAULT now())')
            for p in paths:
                pg.execute('INSERT INTO r4_evidence.migrations(path,sha256) values(%s,%s) on conflict(path) do nothing',(Path(p).name,hashlib.sha256((ROOT/p).read_text('utf8').encode()).hexdigest()))
            receipts[kind]=dict(before_table_count=before,from_empty=before==0,actual_sql=first+middle+final,replay=replay,predecessor=predecessor,
                database_identity=pg.execute('select current_database(),(select oid from pg_database where datname=current_database()),(select system_identifier::text from pg_control_system()),current_setting(\'data_directory\')').fetchone(),
                after=pg.execute("select table_schema,table_name from information_schema.tables where table_schema in ('v4','fep') order by 1,2").fetchall())
        if kind=='upgrade':
            create_database(port,'fep_e1_upgrade',name);create_database(port,'fep_e1_template',name)
    create_database(55793,'fep_authority_isolated')
    with psycopg.connect(admin(55793).replace('dbname=postgres','dbname=fep_authority_isolated'),autocommit=True) as pg:
        pg.execute('CREATE SCHEMA IF NOT EXISTS r4_evidence');pg.execute("CREATE TABLE IF NOT EXISTS r4_evidence.fixture_identity(contract text primary key)");pg.execute("INSERT INTO r4_evidence.fixture_identity VALUES('FEP_AUTHORITY_SYNTHETIC_ENGINEERING_R1') ON CONFLICT DO NOTHING")
    emit('FEP_FRESH_UPGRADE_SQL_R1.json',dict(contract_id='R4_R3_FEP_ACTUAL_FRESH_UPGRADE_R1',run_utc=datetime.now(timezone.utc).isoformat(),fresh_cluster=fresh,upgrade_cluster=upgrade,receipts=receipts,production_changed=False,source_changed=False))
    emit('R3_EXTRA_PG_FIXTURES.json',dict(contract_id='R4_R3_EXPLICIT_ENGINEERING_PG_FIXTURES_R1',databases=[
        dict(database='fep_e5b_fresh',port='55794',data_directory=str(BASE/'fresh_data')),
        *[dict(database=name,port='55793',data_directory=str(BASE/'upgrade_data')) for name in ('fep_e5b_upgrade','fep_e1_upgrade','fep_authority_isolated')]],
        production_authorized=False,source_or_maturity_admission=False))
    return receipts

def project():
    from scripts import run_fep_e5_r1r1b as builder
    from scripts.forward_remainder_pg import typed_pit
    authority_path=SOURCE/'reports/fep_e5_r1r1c/HISTORICAL_RECONSTRUCTION_AUTHORITY_CONTRACT.json'
    input_paths=[authority_path,SOURCE/'reports/fep_e3_r1/EXACT_MODEL_ROWS.jsonl.gz',SOURCE/'reports/fep_e5_r1/POSTGRES_LEDGER_EXPORT.json',SOURCE/'config/fep_e5_projection_priority_protocol_v1.json']
    before={str(p):sha(p) for p in input_paths}
    folder=BASE/'canonical_projection';folder.mkdir(exist_ok=True)
    destination=folder/authority_path.name
    if destination.exists() and destination.read_bytes()!=authority_path.read_bytes():raise ValueError('FROZEN_CANONICAL_AUTHORITY_CONFLICT')
    if not destination.exists():destination.write_bytes(authority_path.read_bytes())
    builder.REPORT=folder;builder.DSNS=DSNS
    builder.old.REPORT=SOURCE/'reports/fep_e5_r1';builder.old.PROTOCOL=SOURCE/'config/fep_e5_projection_priority_protocol_v1.json'
    builder.old.e3.REPORT=SOURCE/'reports/fep_e3_r1'
    def frozen_inputs():
        if {str(p):sha(p) for p in input_paths}!=before:raise ValueError('FROZEN_CANONICAL_INPUT_BYTES_CHANGED')
        return before
    builder.frozen=frozen_inputs
    # Migration 033 requires registering typed signal metadata after its scope.
    # This changes only explicit engineering fixture construction order.
    source=inspect.getsource(ledger.seed_identity).replace('    metadata = register(pg, contract)\n','').replace("    target = metadata['target_row']","    metadata = register(pg, contract)\n    target = metadata['target_row']")
    namespace=dict(ledger.__dict__);exec(compile(source,'<R4_R3_TYPED_033_ENGINEERING_FIXTURE_ORDER>','exec'),namespace)
    original=ledger.seed_identity;ledger.seed_identity=namespace['seed_identity']
    try:builder.project()
    finally:ledger.seed_identity=original
    with psycopg.connect(DSNS['upgrade']) as pg:
        with pg.transaction():typed_pit(pg)
    emit('FEP_CANONICAL_FIXTURE_SOURCE_BINDINGS_R1.json',dict(contract_id='R4_R3_FROZEN_CANONICAL_ENGINEERING_R1',
        input_sha256=before,after_sha256={str(p):sha(p) for p in input_paths},projected_output_root=str(folder),
        REAL_OOS=False,FIRST_OBSERVED=False,production_changed=False,semantic_type='HISTORICAL_RECONSTRUCTION_ENGINEERING_FIXTURE'))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--project',action='store_true');a=p.parse_args()
    install()
    if a.project:project()
    print('FEP explicit engineering fixtures prepared',flush=True)
