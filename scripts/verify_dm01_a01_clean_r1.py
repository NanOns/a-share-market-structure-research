"""Clean detached regression with migrations 001..024 in a disposable database."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
import psycopg

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'src'),str(ROOT/'scripts')]
from scripts.run_v4_08_r3_isolated_verification import disposable_cluster, apply_migrations
from scripts.run_v4_08_r2_regression import REQUIRED_FAMILIES
from scripts.build_v4_08_r2_membership_evidence import atomic_json, atomic_bytes
from scripts.scan_no_symbol_specific_runtime_logic import run as scan
from scripts.verify_v4_08_r5_1 import compact_scan
from workbench_analysis.dm01_accepted_builder_registry import validate_incremental_registry

BASE=ROOT/'reports/dm01'
DESELECT='tests/v4_09/test_stock_prewatch.py::test_production_and_v4_09_acceptance_stay_disabled'
FAMILIES=[*REQUIRED_FAMILIES,'tests/v4_09','tests/v4_10','tests/v4_dm01','tests/test_fixed_qfq_samples.py',
    'tests/test_phase0_2a_gate.py','tests/test_phase1_qa_sample_selector.py','tests/governance/test_no_symbol_specific_runtime_logic.py']

def git(*args):
    return subprocess.run(['git',*args],cwd=ROOT,check=True,capture_output=True,text=True).stdout.strip()

def main():
    before=git('status','--porcelain=v1');head=git('rev-parse','HEAD')
    if before or (ROOT/'config/.env').exists():raise RuntimeError('CLEAN_CHECKOUT_WITHOUT_CONFIG_ENV_REQUIRED')
    protected={r['path']:hashlib.sha256((ROOT/r['path']).read_bytes()).hexdigest() for r in
        json.loads((ROOT/'config/dm01_incremental_builders_contract_r1.json').read_text(encoding='utf8'))['stage_entry_protected_heads']}
    registry=validate_incremental_registry(project_root=ROOT)
    started=time.monotonic()
    with disposable_cluster(Path(r'E:\Postgres\bin')) as (dsn,temp):
        with psycopg.connect(dsn) as pg:
            migrations=apply_migrations(pg)
            identity=pg.execute('SELECT current_database(),current_user,inet_server_addr()::text,inet_server_port()').fetchone()
        if len(migrations)!=24:raise RuntimeError('MIGRATION_ALLOCATION_NOT_001_TO_024')
        guard=temp/'guard';guard.mkdir()
        (guard/'sitecustomize.py').write_text("import sys,os\ndef forbid(event,args):\n if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)):\n  path=os.fsdecode(args[0]).replace('\\\\','/').lower()\n  if path.endswith('/config/.env'):raise RuntimeError('CONFIG_ENV_READ_FORBIDDEN')\nsys.addaudithook(forbid)\n",encoding='utf8')
        env=os.environ.copy();env.update(WORKBENCH_PG_DSN=dsn,V4_10_DISPOSABLE_TEST_DSN=dsn,
            PYTHONPATH=str(guard)+os.pathsep+str(ROOT)+os.pathsep+str(ROOT/'src'),PYTHONIOENCODING='utf-8')
        for k in ['PGPASSWORD','PGSERVICE','PGSERVICEFILE']:env.pop(k,None)
        junit=temp/'tests.xml'
        command=[sys.executable,'-m','pytest','-q',*FAMILIES,'--deselect='+DESELECT,f'--junitxml={junit}']
        proc=subprocess.run(command,cwd=ROOT,env=env,capture_output=True,text=True,encoding='utf8',errors='replace',timeout=1200)
        nodes=list(ET.parse(junit).getroot().iter('testsuite')) if junit.exists() else []
        summary={k:sum(int(n.attrib.get(k,0)) for n in nodes) for k in ['tests','failures','errors','skipped']}
        summary['passed']=summary['tests']-summary['failures']-summary['errors']-summary['skipped']
        junit_bytes=junit.read_bytes() if junit.exists() else b''
    governance=scan(ROOT)
    after=git('status','--porcelain=v1')
    unchanged=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==s for p,s in protected.items())
    ok=proc.returncode==0 and bool(nodes) and not after and unchanged and governance['status']=='PASS' and registry['status'].startswith('PASS')
    atomic_bytes(BASE/'DM01_A01_CLEAN_REGRESSION_R1.xml',junit_bytes)
    atomic_bytes(BASE/'DM01_A01_CLEAN_REGRESSION_R1.log',(proc.stdout+'\n'+proc.stderr).encode('utf8'))
    atomic_json(BASE/'DM01_A01_NO_SYMBOL_SCAN_R1.json',compact_scan(governance))
    receipt=dict(contract_id='DM01_A01_CLEAN_CHECKOUT_R1',status='PASS' if ok else 'FAIL',tested_commit=head,
        git_status_before=before,git_status_after=after,config_dot_env_present=False,config_dot_env_read=False,
        configured_or_production_database_used=False,temporary_cluster_cleaned_up=True,password_persisted=False,
        database_identity=dict(zip(['database','owner','server_address','server_port'],identity)),migrations=migrations,
        required_families=FAMILIES,authorized_deselects=[DESELECT],new_deselects=[],summary=summary,
        pytest_return_code=proc.returncode,junit_sha256=hashlib.sha256(junit_bytes).hexdigest(),
        protected_heads=protected,protected_heads_unchanged=unchanged,registry=registry,no_symbol_status=governance['status'],
        elapsed_seconds=round(time.monotonic()-started,3),created_at_utc=datetime.now(timezone.utc).isoformat(),
        acceptance_scope='ENGINEERING_REGRESSION_ONLY_REAL_MARKET_SOURCE_GATE_SEPARATE',external_acceptance='PENDING')
    atomic_json(BASE/'DM01_A01_CLEAN_CHECKOUT_R1.json',receipt)
    print(json.dumps(dict(status=receipt['status'],summary=summary,no_symbol=governance['status'])))
    return 0 if ok else 1

if __name__=='__main__':raise SystemExit(main())
