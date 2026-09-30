"""Final clean detached reproduction and regression using disposable PostgreSQL only."""
from copy import deepcopy
from datetime import datetime,timezone
import argparse
import gzip
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'src'))
from scripts.run_v4_08_r2_regression import REQUIRED_FAMILIES
from scripts.run_v4_08_r3_isolated_verification import disposable_cluster,apply_migrations,verify_schema
from scripts.build_v4_08_r2_membership_evidence import atomic_json
from scripts.verify_v4_08_r5_1 import compact_scan
from scripts.promote_v4_08_accepted_head import validate as promotion_validation
from src.v4.stock_prewatch import digest
from src.v4.stock_prewatch_persistence import persist

def git(*args):
    return subprocess.run(['git',*args],cwd=ROOT,text=True,capture_output=True,check=True).stdout.strip()

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--postgres-bin',type=Path,default=Path(r'E:\Postgres\bin'));args=parser.parse_args()
    before=git('status','--porcelain=v1'); head=git('rev-parse','HEAD'); started=time.monotonic()
    if before or git('branch','--show-current') or (ROOT/'config/.env').exists(): raise ValueError('CLEAN_DETACHED_WITHOUT_DOT_ENV_REQUIRED')
    promotion=promotion_validation()
    if promotion['status']!='PASS': raise ValueError('PROMOTION_VALIDATION_FAILED')
    reproduction=[]
    for script in ['materialize_v4_09_stock_prewatch.py','verify_v4_09_stock_prewatch.py']:
        p=subprocess.run([sys.executable,str(ROOT/'scripts'/script)],cwd=ROOT,capture_output=True,text=True,encoding='utf8',errors='replace',check=True)
        reproduction.append(dict(script=script,stdout=p.stdout))
    if git('status','--porcelain=v1'): raise ValueError('CANDIDATE_REPRODUCTION_CHANGED_TRACKED_BYTES')
    receipt=json.loads((ROOT/'reports/v4_09/V4_09_FULL_MARKET_CANDIDATE.json').read_text(encoding='utf8'))
    with gzip.open(ROOT/receipt['artifact']['path'],'rt',encoding='utf8') as stream: records=[json.loads(line) for line in stream]
    with disposable_cluster(args.postgres_bin) as (dsn,temp):
        import psycopg
        with psycopg.connect(dsn) as pg:
            identity=pg.execute("SELECT current_database(),current_user,inet_server_addr()::text,inet_server_port(),version(),datcollate,datctype FROM pg_database WHERE datname=current_database()").fetchone()
            migrations=apply_migrations(pg);checks=verify_schema(pg)
            readback=persist(pg,records); retry=persist(pg,records)
            checks['V4_09_exact_readback']=readback['row_count']==receipt['row_count'] and readback['publication_digest']==receipt['artifact']['logical_digest']
            checks['V4_09_same_publication_security_idempotent']=readback==retry
            revised=deepcopy(records)
            for row in revised: row['publication_id']+=':revision-2'
            second=persist(pg,revised)
            checks['V4_09_different_revision_append_only']=pg.execute('SELECT count(*) FROM v4.stock_prewatch_results').fetchone()[0]==len(records)+len(revised)
            def rejected(sql):
                try:
                    with pg.transaction(): pg.execute(sql)
                except psycopg.Error: return True
                return False
            checks['V4_09_rows_update_rejected']=rejected('UPDATE v4.stock_prewatch_results SET quality=quality')
            checks['V4_09_rows_delete_rejected']=rejected('DELETE FROM v4.stock_prewatch_results')
            checks['V4_09_publication_update_rejected']=rejected('UPDATE v4.stock_prewatch_publications SET row_count=row_count')
            checks['V4_09_publication_delete_rejected']=rejected('DELETE FROM v4.stock_prewatch_publications')
            changed=deepcopy(records);changed[0]['quality']='MUTATED'
            try: persist(pg,changed)
            except ValueError: checks['V4_09_same_publication_conflict_rejected']=True
            else: checks['V4_09_same_publication_conflict_rejected']=False
            before_tables={r[0] for r in pg.execute("SELECT tablename FROM pg_tables WHERE schemaname='v4'").fetchall()}
            before_functions={r[0] for r in pg.execute("SELECT oid::regprocedure::text FROM pg_proc WHERE pronamespace='v4'::regnamespace").fetchall()}
            with pg.transaction():
                pg.execute('SAVEPOINT rollback_021_probe')
                pg.execute((ROOT/'src/workbench_db/migrations/v4_postgres/rollback/021_v4_09_stock_prewatch.sql').read_text(encoding='utf8'))
                after_tables={r[0] for r in pg.execute("SELECT tablename FROM pg_tables WHERE schemaname='v4'").fetchall()}
                after_functions={r[0] for r in pg.execute("SELECT oid::regprocedure::text FROM pg_proc WHERE pronamespace='v4'::regnamespace").fetchall()}
                checks['V4_09_rollback_only_021_objects']=before_tables-after_tables=={'stock_prewatch_results','stock_prewatch_publications'} and before_functions-after_functions=={'v4.guard_stock_prewatch_binding()'}
                pg.execute('ROLLBACK TO SAVEPOINT rollback_021_probe')
            checks['V4_09_rollback_probe_restored_exact_rows']=persist(pg,records)==readback and persist(pg,revised)==second
            schema=dict(contract_id='V4_09_SCHEMA_MIGRATION_RECEIPT_V1',status='PASS' if all(checks.values()) else 'FAIL',tested_commit=head,
                database_identity=dict(zip(['database','owner','server_address','server_port','version','datcollate','datctype'],identity)),
                migrations=migrations,checks=checks,full_market_readback=readback,revision_readback=second,
                config_dot_env_read=False,configured_or_production_database_used=False,credentials_persisted=False,temporary_cluster_destroyed=True)
            if schema['status']!='PASS': raise ValueError(checks)
        guard=temp/'guard';guard.mkdir()
        (guard/'sitecustomize.py').write_bytes(b"import sys,os\ndef forbid(event,args):\n if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)) and os.fsdecode(args[0]).replace('\\\\','/').lower().endswith('/config/.env'): raise RuntimeError('CONFIG_DOT_ENV_READ_FORBIDDEN')\nsys.addaudithook(forbid)\n")
        env=os.environ.copy();env['WORKBENCH_PG_DSN']=dsn;env['PYTHONPATH']=str(guard)+os.pathsep+str(ROOT)+os.pathsep+env.get('PYTHONPATH','')
        for key in ['PGPASSWORD','PGSERVICE','PGSERVICEFILE']:env.pop(key,None)
        families=[*REQUIRED_FAMILIES,'tests/v4_09','tests/test_fixed_qfq_samples.py','tests/test_phase0_2a_gate.py','tests/test_phase1_qa_sample_selector.py','tests/governance/test_no_symbol_specific_runtime_logic.py']
        junit=temp/'junit.xml'
        p=subprocess.run([sys.executable,'-m','pytest','-q',*families,f'--junitxml={junit}'],cwd=ROOT,env=env,capture_output=True,text=True,encoding='utf8',errors='replace',timeout=1200)
        suites=list(ET.parse(junit).getroot().iter('testsuite')) if junit.exists() else []
        summary={k:sum(int(s.attrib.get(k,0)) for s in suites) for k in ['tests','failures','errors','skipped']}
        summary['passed']=summary['tests']-summary['failures']-summary['errors']-summary['skipped']
        regression=dict(contract_id='V4_09_ISOLATED_REGRESSION_V1',status='PASS' if p.returncode==0 and suites else 'FAIL',tested_commit=head,
            summary=summary,required_families=families,stdout=p.stdout,stderr=p.stderr,config_dot_env_read=False,
            dsn_source='PROCESS_ENVIRONMENT_DISPOSABLE_CLUSTER',configured_or_production_database_used=False)
    from scripts.scan_no_symbol_specific_runtime_logic import run as scan
    governance=scan(ROOT);governance['tested_commit']=head
    after=git('status','--porcelain=v1')
    clean=dict(contract_id='V4_09_CLEAN_CHECKOUT_RECEIPT_V1',status='PASS_CLEAN_DETACHED_CHECKOUT' if not after and schema['status']=='PASS' and regression['status']=='PASS' and governance['status']=='PASS' else 'FAIL',
        tested_commit=head,detached_head=True,git_status_before=before,git_status_after=after,config_dot_env_present=False,
        temporary_cluster_destroyed=True,promotion_validation=promotion,reproduction=reproduction,
        elapsed_seconds=round(time.monotonic()-started,3),created_at_utc=datetime.now(timezone.utc).isoformat())
    out=ROOT/'reports/v4_09'
    for name,value in [('SCHEMA_MIGRATION_RECEIPT',schema),('ISOLATED_REGRESSION',regression),('CLEAN_CHECKOUT_RECEIPT',clean),('NO_SYMBOL_SPECIFIC_SYSTEM_LOGIC_SCAN',compact_scan(governance))]:
        atomic_json(out/f'V4_09_{name}.json',value)
    print(json.dumps(dict(status=clean['status'],tested_commit=head,regression=summary,no_symbol_status=governance['status'],checks=checks)))
    return 0 if clean['status'].startswith('PASS') else 1

if __name__=='__main__':sys.exit(main())
