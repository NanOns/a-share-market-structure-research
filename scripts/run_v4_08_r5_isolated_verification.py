"""Clean-checkout R5 regression and migrations on a disposable PostgreSQL cluster."""
from __future__ import annotations
from datetime import datetime,timezone
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import gzip
import tempfile
import time
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/'src'))
sys.path.insert(0,str(ROOT/'scripts'))
from scripts.run_v4_08_r2_regression import REQUIRED_FAMILIES
from scripts.run_v4_08_r3_isolated_verification import disposable_cluster,apply_migrations,verify_schema
from scripts.build_v4_08_r2_membership_evidence import atomic_json

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def git(*args):return subprocess.run(['git',*args],cwd=ROOT,text=True,capture_output=True,check=True).stdout.strip()

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--postgres-bin',type=Path,default=Path(r'E:\Postgres\bin'));args=parser.parse_args()
    if (ROOT/'config/.env').exists():raise RuntimeError('R5 clean checkout must not contain config/.env')
    before=git('status','--porcelain=v1')
    if before:raise RuntimeError('R5 checkout must be clean before verification')
    head=git('rev-parse','HEAD');started=time.monotonic();schema_receipt=None;regression=None
    with disposable_cluster(args.postgres_bin) as (dsn,temp):
        import psycopg
        with psycopg.connect(dsn) as pg:
            database=pg.execute("SELECT current_database(),current_user,inet_server_addr()::text,inet_server_port(),version(),datcollate,datctype FROM pg_database WHERE datname=current_database()").fetchone()
            migrations=apply_migrations(pg);checks=verify_schema(pg)
            from sector.persistence_r5 import persist
            records=[]
            manifest=json.loads((ROOT/'reports/v4_08/V4_08_R5_STAGE_CANDIDATE_MANIFEST.json').read_text(encoding='utf8'))
            for binding in manifest['artifacts'].values():
                path=ROOT/binding['path']
                if sha(path)!=binding['sha256']:raise RuntimeError('R5_ARTIFACT_DIGEST_MISMATCH')
                with gzip.open(path,'rt',encoding='utf8') as stream:records.extend(json.loads(line) for line in stream)
            readback=persist(pg,records)
            retry=persist(pg,records)
            checks['R5_full_market_1512_rows_exact_readback']=readback['row_count']==1512 and readback==retry
            checks['R5_append_only_results']=False
            try:
                with pg.transaction():pg.execute('UPDATE v4.sector_algorithm_results_r5 SET quality=quality')
            except psycopg.Error:checks['R5_append_only_results']=True
            checks['R5_append_only_publication']=False
            try:
                with pg.transaction():pg.execute('DELETE FROM v4.sector_algorithm_publications_r5')
            except psycopg.Error:checks['R5_append_only_publication']=True

        schema_receipt={'contract_id':'V4_08_R5_SCHEMA_MIGRATION_RECEIPT_V1','status':'PASS' if all(checks.values()) else 'FAIL','tested_commit':head,'database_identity':dict(zip(['database','owner','server_address','server_port','version','datcollate','datctype'],database)),'migrations':migrations,'checks':checks,'full_market_readback':readback,'dsn_source':'PROCESS_ENVIRONMENT_DISPOSABLE_CLUSTER','config_dot_env_read':False,'configured_or_production_database_used':False,'temporary_cluster_destroyed':True,'credentials_persisted':False}
        if not all(checks.values()):raise RuntimeError('R5 migration/schema contract checks failed')
        guard=temp/'guard';guard.mkdir()
        (guard/'sitecustomize.py').write_text('''import sys, os\ndef forbid_config_env(event,args):\n if event == 'open' and isinstance(args[0],(str,bytes,os.PathLike)):\n  path=os.fsdecode(args[0]).replace('\\\\','/').lower()\n  if path.endswith('/config/.env'): raise RuntimeError('CONFIG_DOT_ENV_READ_FORBIDDEN_IN_R5_REGRESSION')\nsys.addaudithook(forbid_config_env)\n''',encoding='utf-8')
        env=os.environ.copy();env['WORKBENCH_PG_DSN']=dsn;env['PYTHONPATH']=str(guard)+os.pathsep+str(ROOT)+os.pathsep+env.get('PYTHONPATH','')
        for key in ['PGPASSWORD','PGSERVICE','PGSERVICEFILE']:env.pop(key,None)
        junit=temp/'junit.xml';families=[*REQUIRED_FAMILIES,
            'tests/test_fixed_qfq_samples.py','tests/test_phase0_2a_gate.py',
            'tests/test_phase1_qa_sample_selector.py',
            'tests/governance/test_no_symbol_specific_runtime_logic.py']
        proc=subprocess.run([sys.executable,'-m','pytest','-q',*families,f'--junitxml={junit}'],cwd=ROOT,env=env,text=True,capture_output=True,encoding='utf-8',errors='replace',timeout=900)
        suites=list(ET.parse(junit).getroot().iter('testsuite')) if junit.exists() else []
        summary={key:sum(int(node.attrib.get(key,0)) for node in suites) for key in ['tests','failures','errors','skipped']}
        summary['passed']=summary['tests']-summary['failures']-summary['errors']-summary['skipped']
        regression={'contract_id':'V4_08_R5_ISOLATED_REGRESSION_V1','status':'PASS' if proc.returncode==0 and suites and summary['failures']==0 and summary['errors']==0 else 'FAIL','tested_commit':head,'summary':summary,'pytest_return_code':proc.returncode,'required_families':families,'stdout':proc.stdout,'stderr':proc.stderr,'junit_sha256':sha(junit) if junit.exists() else None,'config_dot_env_read':False,'dsn_source':'PROCESS_ENVIRONMENT_DISPOSABLE_CLUSTER'}
    from scripts.scan_no_symbol_specific_runtime_logic import run as governance_scan
    governance=governance_scan(ROOT)
    governance['tested_commit']=head
    if governance['status']!='PASS':raise RuntimeError('R5_NO_SYMBOL_HARD_GATE_FAILED')
    after=git('status','--porcelain=v1')
    clean={'contract_id':'V4_08_R5_CLEAN_CHECKOUT_RECEIPT_V1','status':'PASS_CLEAN_DETACHED_CHECKOUT' if not before and not after and git('branch','--show-current')=='' else 'FAIL','tested_commit':head,'detached_head':git('branch','--show-current')=='','git_status_before':before,'git_status_after':after,'config_dot_env_present':(ROOT/'config/.env').exists(),'schema_migration_receipt':schema_receipt,'isolated_regression_receipt':regression,'temporary_cluster_destroyed':True,'elapsed_seconds':round(time.monotonic()-started,3),'created_at_utc':datetime.now(timezone.utc).isoformat()}
    clean['status']='PASS_CLEAN_DETACHED_CHECKOUT' if clean['status']=='PASS_CLEAN_DETACHED_CHECKOUT' and schema_receipt['status']=='PASS' and regression['status']=='PASS' else 'FAIL'
    out=ROOT/'reports/v4_08';atomic_json(out/'V4_08_R5_SCHEMA_MIGRATION_RECEIPT.json',schema_receipt);atomic_json(out/'V4_08_R5_ISOLATED_REGRESSION.json',regression);atomic_json(out/'V4_08_R5_CLEAN_CHECKOUT_RECEIPT.json',clean);atomic_json(out/'V4_08_R5_NO_SYMBOL_SPECIFIC_SYSTEM_LOGIC_SCAN.json',governance)
    print(json.dumps({'status':clean['status'],'tested_commit':head,'database_identity':schema_receipt['database_identity'],'regression':summary,'git_clean_before_after':not before and not after,'temporary_cluster_destroyed':True}))
    return 0 if clean['status']=='PASS_CLEAN_DETACHED_CHECKOUT' else 1

if __name__=='__main__':raise SystemExit(main())
