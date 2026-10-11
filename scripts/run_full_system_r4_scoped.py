"""Reproducible bounded R4 engineering run; never claims full regression."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid
import xml.etree.ElementTree as ET
import hashlib
import argparse

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
OUT=ROOT/'docs/audits/full_system_r4_pg_only_20261011_fbd23a6b'
FILES=['tests/test_v4_pg_jobs_r4.py','tests/test_v4_pg_storage_r4.py','tests/test_v4_pg_journal_r4.py','tests/test_v4_exact_transport_r4.py','tests/test_operational_daily_jobs_v1.py','tests/test_audit_repair_adjustment_r3.py']
FILES+=['tests/test_r2_journal.py','tests/test_audit_repair_home_r3.py','tests/test_audit_repair_storage_r3.py','tests/test_audit_repair_compare_r3.py','tests/test_audit_repair_loo_r3.py']
FILES+=['tests/test_dynamic_daily_r21_repair.py']
FILES+=['tests/test_v4_pure_rank_r4.py','tests/test_v4_readonly_source_guard_r4.py','tests/test_next_stage_c_episode_genesis.py::test_independent_average_rank_oracle_with_ties_and_unstable_delta']
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--profile',choices=['native','fep_e1'],default='native');args=parser.parse_args()
    files=FILES if args.profile=='native' else ['tests/fep/'+name for name in ('test_database.py','test_cas_roles.py','test_feature_owner.py','test_namespace.py','test_pipeline.py','test_r1_label_time.py','test_v4_18_namespace_successor.py')]
    if args.profile=='fep_e1':files+=['tests/test_v4_pg_jobs_r4.py::test_guard_cannot_satisfy_business_exception','tests/test_v4_pg_jobs_r4.py::test_pg_disconnect_fails_closed_without_file']
    name='R4_SCOPED_'+uuid.uuid4().hex[:8]
    env=dict(os.environ,TMP='G:/codex_tmp',TEMP='G:/codex_tmp',TMPDIR='G:/codex_tmp',PYTHONDONTWRITEBYTECODE='1',PYTHONUTF8='1',PYTHONPATH=os.pathsep.join([str(ROOT/'src'),str(ROOT)]),R4_NATIVE_ISOLATION='1',R4_PG_DATA_DIRECTORY='G:/codex_tmp/full_system_r4_fbd23a6b/pg_data',R4_CONNECTION_LEDGER=str(OUT/(name+'_CONNECTIONS.jsonl')))
    if 'V4_NATIVE_PG_DSN' not in env:raise ValueError('EXPLICIT_R4_PG_DSN_REQUIRED')
    xml=OUT/(name+'_JUNIT.xml');log=OUT/(name+'.log')
    command=[sys.executable,'-B','-m','pytest','-q',*files,'--basetemp=G:/codex_tmp/test_temp/'+name,'-o','cache_dir=G:/codex_tmp/pytest_cache_r4','--junitxml='+str(xml)]
    start=time.time()
    with log.open('w',encoding='utf8') as stream: result=subprocess.run(command,cwd=ROOT,env=env,stdout=stream,stderr=subprocess.STDOUT)
    cases=ET.parse(xml).findall('.//testcase');counts={s:0 for s in ['PASS','FAIL','ERROR','SKIP']}
    for c in cases:counts['FAIL' if c.find('failure') is not None else 'ERROR' if c.find('error') is not None else 'SKIP' if c.find('skipped') is not None else 'PASS']+=1
    from scripts.audit_full_system_r4_scope import write
    sources={p:hashlib.sha256((ROOT/p.split('::')[0]).read_bytes()).hexdigest() for p in files}
    write(name+'_RESULT.json',dict(contract_id='R4_SCOPED_ENGINEERING_EXECUTION_R1',current_status='SCOPED_TEST_PASS' if result.returncode==0 else 'SCOPED_TEST_FAIL',denominator=len(cases),results=counts,seconds=time.time()-start,command=command,source_bindings=sources,evidence_links=[xml.name,log.name,name+'_CONNECTIONS.jsonl'],limitations=['Named engineering modules; this is not the full V4 legal regression denominator'],next_conditions=['Complete per-module scope review and full clean-slate run']))
    print(json.dumps(dict(name=name,counts=counts,exit_code=result.returncode,seconds=time.time()-start)))
    return result.returncode
if __name__=='__main__':raise SystemExit(main())
