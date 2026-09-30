"""R3 independent SQL vectors and full regression against a disposable cluster."""
from __future__ import annotations
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
import psycopg

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.apply_v4_phase0_schema import VERSIONS
from scripts.build_v4_08_r2_membership_evidence import atomic_json
from scripts.run_v4_08_r2_regression import REQUIRED_FAMILIES

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

@contextmanager
def disposable_cluster(pg_bin: Path):
    temporary = tempfile.TemporaryDirectory(prefix='v4_08_r3_isolated_pg_')
    temp = Path(temporary.name)
    data = temp / 'pgdata'
    def run(args, **kwargs):
        return subprocess.run([str(x) for x in args], check=True, timeout=75,
                              creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **kwargs)
    def exe(name):
        return pg_bin / (name + ('.exe' if os.name == 'nt' else ''))
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0)); port = sock.getsockname()[1]
    started = False
    try:
        run([exe('initdb'), '-D', data, '-U', 'postgres', '--auth=trust', '--encoding=UTF8', '--locale=C'])
        run([exe('pg_ctl'), '-D', data, '-o', f'-h 127.0.0.1 -p {port}', '-l', temp/'postgres.log', '-w', 'start'])
        started = True
        connection = f'host=127.0.0.1 port={port} user=postgres dbname=postgres'
        with psycopg.connect(connection, autocommit=True) as pg:
            pg.execute('''CREATE DATABASE market_research OWNER postgres ENCODING 'UTF8'
                         LC_COLLATE 'Chinese (Simplified)_China.936' LC_CTYPE 'Chinese (Simplified)_China.936' TEMPLATE template0''')
        yield f'host=127.0.0.1 port={port} user=postgres dbname=market_research', temp
    finally:
        if started or (data / 'postmaster.pid').exists():
            run([exe('pg_ctl'), '-D', data, '-m', 'immediate', '-w', 'stop'])
        temporary.cleanup()
        if temp.exists():
            raise RuntimeError('disposable cluster cleanup failed')

def apply_migrations(pg):
    receipts=[]
    for path in sorted((ROOT/'src/workbench_db/migrations/v4_postgres').glob('*.sql')):
        with pg.transaction():
            pg.execute(path.read_text(encoding='utf-8'))
            version=VERSIONS.get(path.name, 'V4_STAGE_' + path.stem.upper())
            checksum=hashlib.sha256(path.read_text(encoding='utf-8').encode()).hexdigest()
            pg.execute('INSERT INTO v4_meta.schema_migrations VALUES (%s,%s,now(),%s)', (version,checksum,version))
        receipts.append({'path':path.relative_to(ROOT).as_posix(),'sha256':digest(path),'version':version})
    return receipts

def verify_schema(pg):
    checks={}
    def rejected(operation, phrase):
        try:
            with pg.transaction(): operation()
        except psycopg.Error as error:
            return phrase in str(error)
        return False
    with pg.transaction():
        pg.execute('SAVEPOINT fixture_scope')
        registry=pg.execute('SELECT registry_digest FROM v4.sector_membership_type_policy LIMIT 1').fetchone()[0].strip()
        def revision(rev, basis='PIT_OBSERVED', quality='PIT_OBSERVED_ACCEPTED'):
            pg.execute('''INSERT INTO v4.sector_membership_source_revisions
            (source_revision_id,source_contract_id,source_digest,source_file_digests,observed_at,ingested_at,system_available_at,provider_available_at,membership_asof_date,membership_basis,created_at,source_bytes_digest,temporal_evidence_digest,temporal_evidence,provider_available_at_basis,membership_asof_basis,revision_quality)
            VALUES (%s,'V4_08_SECTOR_MEMBERSHIP_SOURCE_V1',%s,'{}','2026-09-30T01:00Z','2026-09-30T01:01Z','2026-09-30T01:01Z','2026-09-30T01:00Z','2026-09-30',%s,now(),%s,%s,'{"revision_chain_valid":true}','PROJECT_FIRST_OBSERVED_PROVIDER_BYTES','PROJECT_FIRST_OBSERVED_SOURCE_STATE',%s)''',
            (rev,'a'*64,basis,'b'*64,'c'*64,quality))
        def snapshot(sid, rev, basis='PIT_OBSERVED', quality='PIT_OBSERVED_ACCEPTED'):
            pg.execute('''INSERT INTO v4.sector_membership_snapshots
            (snapshot_id,target_trade_date,cutoff,sector_type_registry_digest,source_revision_id,source_digest,source_file_digests,membership_basis,membership_quality,pit_observed,historical_backtest_safe,row_count,created_at,snapshot_lineage_role)
            VALUES (%s,'2026-09-30','2026-09-30T02:00Z',%s,%s,%s,'{}',%s,%s,%s,%s,1,now(),%s)''',
            (sid,registry,rev,'a'*64,basis,quality,basis=='PIT_OBSERVED',quality=='PIT_OBSERVED_ACCEPTED','FORWARD_PIT_CANDIDATE' if basis=='PIT_OBSERVED' else 'RAW_CURRENT'))
        def fact(fid,sid,rev,basis='PIT_OBSERVED',quality='PIT_OBSERVED_ACCEPTED'):
            pg.execute('''INSERT INTO v4.sector_membership_facts
            (membership_fact_id,snapshot_id,source_revision_id,sector_id,sector_code,sector_name,sector_type,source_sector_type,source_security_key,security_id,identity_status,target_trade_date,membership_asof_date,cutoff,membership_basis,membership_quality,pit_observed,historical_backtest_safe,created_at)
            VALUES (%s,%s,%s,'INDUSTRY:fixture','fixture','fixture','INDUSTRY','industry','SH.600001','fixture-security','MAPPED','2026-09-30','2026-09-30','2026-09-30T02:00Z',%s,%s,%s,%s,now())''',
            (fid,sid,rev,basis,quality,basis=='PIT_OBSERVED',quality=='PIT_OBSERVED_ACCEPTED'))
        revision('r3-positive'); snapshot('1'*64,'r3-positive'); fact('1'*64,'1'*64,'r3-positive')
        checks['positive_pit_formal_fact_visible']=pg.execute('SELECT count(*) FROM v4.formal_sector_membership').fetchone()[0]==1
        checks['B07_revision_insert_rejects_current_with_pit_quality']=rejected(lambda: revision('r3-evil','CURRENT_TDX_MEMBERSHIP'), 'ck_v4_sector_revision_basis_quality_r3')
        revision('r3-current','CURRENT_TDX_MEMBERSHIP','CURRENT_TDX_DIAGNOSTIC')
        checks['B07_snapshot_trigger_rejects_mixed_source_basis']=rejected(lambda:snapshot('2'*64,'r3-current'), 'source revision basis')
        checks['B07_fact_trigger_rejects_mixed_source_basis']=rejected(lambda:fact('2'*64,'1'*64,'r3-current'), 'R3 source revision snapshot fact basis mismatch')
        compatibility=[('PIT_OBSERVED_ACCEPTED','PIT_OBSERVED'),('CURRENT_TDX_DIAGNOSTIC','CURRENT_TDX_MEMBERSHIP'),('CURRENT_REPLAY_DIAGNOSTIC','CURRENT_MEMBERSHIP_REPLAY'),('DERIVED_PARENT_DIAGNOSTIC','DERIVED_PARENT_MEMBERSHIP')]
        checks['basis_quality_four_pairs']=all(pg.execute('SELECT v4.sector_membership_basis_quality_compatible_r3(%s,%s)',(b,q)).fetchone()[0] for q,b in compatibility)
        checks['basis_quality_cross_pairs_rejected']=all(not pg.execute('SELECT v4.sector_membership_basis_quality_compatible_r3(%s,%s)',(b2,q)).fetchone()[0] for q,b in compatibility for _,b2 in compatibility if b!=b2)
        # Simulate corrupt imported rows only inside an explicitly rolled-back savepoint.
        pg.execute('SAVEPOINT corrupt_import')
        pg.execute('ALTER TABLE v4.sector_membership_source_revisions DROP CONSTRAINT ck_v4_sector_revision_basis_quality_r3')
        pg.execute('SET LOCAL session_replication_role = replica')
        revision('r3-corrupt','CURRENT_TDX_MEMBERSHIP')
        snapshot('3'*64,'r3-corrupt'); fact('3'*64,'3'*64,'r3-corrupt')
        checks['B07_formal_view_rejects_corrupt_mixed_basis']=pg.execute("SELECT count(*) FROM v4.formal_sector_membership WHERE source_revision_id='r3-corrupt'").fetchone()[0]==0
        pg.execute('ROLLBACK TO SAVEPOINT corrupt_import')
        pg.execute('ROLLBACK TO SAVEPOINT fixture_scope')
    rollback=ROOT/'src/workbench_db/migrations/v4_postgres/rollback/019_v4_08_membership_source_basis_guard_r3.sql'
    with pg.transaction():
        pg.execute('SAVEPOINT rollback_probe')
        pg.execute(rollback.read_text(encoding='utf-8'))
        checks['rollback_removes_only_r3']=pg.execute("SELECT to_regprocedure('v4.check_sector_membership_fact_source_basis_r3()') IS NULL AND to_regprocedure('v4.check_sector_membership_fact_temporal_binding()') IS NOT NULL AND to_regclass('v4.sector_membership_facts') IS NOT NULL").fetchone()[0]
        pg.execute('ROLLBACK TO SAVEPOINT rollback_probe')
    return checks

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--regression',action='store_true');parser.add_argument('--postgres-bin',type=Path,default=Path(r'E:\Postgres\bin'));args=parser.parse_args()
    if args.regression and (ROOT/'config/.env').exists():
        raise RuntimeError('clean regression checkout must have no config/.env')
    before=subprocess.run(['git','status','--porcelain=v1'],cwd=ROOT,text=True,capture_output=True,check=True).stdout.strip()
    if args.regression and before: raise RuntimeError('regression checkout is not clean')
    head=subprocess.run(['git','rev-parse','HEAD'],cwd=ROOT,text=True,capture_output=True,check=True).stdout.strip()
    started=time.monotonic(); regression=None
    with disposable_cluster(args.postgres_bin) as (dsn,temp):
        with psycopg.connect(dsn) as pg:
            identity=pg.execute("SELECT current_database(),current_user,inet_server_addr()::text,inet_server_port(),version(),datcollate,datctype FROM pg_database WHERE datname=current_database()").fetchone()
            migrations=apply_migrations(pg)
            checks=verify_schema(pg)
        if args.regression:
            guard=temp/'guard';guard.mkdir()
            (guard/'sitecustomize.py').write_text('''import sys, os
def forbid_config_env(event,args):
 if event == 'open' and isinstance(args[0],(str,bytes,os.PathLike)):
  path=os.fsdecode(args[0]).replace('\\\\','/').lower()
  if path.endswith('/config/.env'): raise RuntimeError('CONFIG_DOT_ENV_READ_FORBIDDEN_IN_R3_REGRESSION')
sys.addaudithook(forbid_config_env)
''',encoding='utf-8')
            env=os.environ.copy();env['WORKBENCH_PG_DSN']=dsn;env['PYTHONPATH']=str(guard)+os.pathsep+str(ROOT)+os.pathsep+env.get('PYTHONPATH','')
            for key in ['PGPASSWORD','PGSERVICE','PGSERVICEFILE']:env.pop(key,None)
            junit=temp/'junit.xml'
            proc=subprocess.run([sys.executable,'-m','pytest','-q',*REQUIRED_FAMILIES,f'--junitxml={junit}'],cwd=ROOT,env=env,text=True,capture_output=True,encoding='utf-8',errors='replace',timeout=600)
            suites=list(ET.parse(junit).getroot().iter('testsuite')) if junit.exists() else []
            summary={k:sum(int(n.attrib.get(k,0)) for n in suites) for k in ['tests','failures','errors','skipped']}
            summary['passed']=summary['tests']-summary['failures']-summary['errors']-summary['skipped']
            regression={'status':'PASS' if proc.returncode==0 and suites else 'FAIL','summary':summary,'pytest_return_code':proc.returncode,'required_families':REQUIRED_FAMILIES,'stdout':proc.stdout,'stderr':proc.stderr,'junit_sha256':digest(junit) if junit.exists() else None}
    after=subprocess.run(['git','status','--porcelain=v1'],cwd=ROOT,text=True,capture_output=True,check=True).stdout.strip()
    receipt={'contract_id':'V4_08_R3_ISOLATED_VERIFICATION_V1','status':'PASS' if all(checks.values()) and (regression is None or regression['status']=='PASS') else 'FAIL','tested_commit':head,'database_identity':dict(zip(['database','owner','server_address','server_port','version','datcollate','datctype'],identity)),'configured_or_production_database_used':False,'config_dot_env_read':False,'dsn_source':'PROCESS_ENVIRONMENT_DISPOSABLE_CLUSTER','temporary_cluster_cleaned_up':True,'password_persisted':False,'checks':checks,'migrations':migrations,'rollback_sha256':digest(ROOT/'src/workbench_db/migrations/v4_postgres/rollback/019_v4_08_membership_source_basis_guard_r3.sql'),'elapsed_seconds':round(time.monotonic()-started,3),'created_at_utc':datetime.now(timezone.utc).isoformat(),'regression':regression,'git_status_before':before,'git_status_after':after}
    base=ROOT/'reports/v4_08'
    if args.regression:
        atomic_json(base/'V4_08_R3_ISOLATED_REGRESSION.json',receipt)
        atomic_json(base/'V4_08_R3_CLEAN_CHECKOUT_RECEIPT.json',{**receipt,'status':'PASS_CLEAN_CHECKOUT_DISPOSABLE_DATABASE' if receipt['status']=='PASS' and not before and not after else 'FAIL'})
    else: atomic_json(base/'V4_08_R3_SCHEMA_MIGRATION_RECEIPT.json',receipt)
    print(json.dumps({'status':receipt['status'],'checks':checks,'regression':regression['summary'] if regression else None,'cluster_cleaned_up':True}))
    return 0 if receipt['status']=='PASS' else 1

if __name__=='__main__':raise SystemExit(main())
