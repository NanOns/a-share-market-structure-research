"""Immutable tested source, clean detached regression and evidence-only seal."""
import os,sys,json,subprocess,xml.etree.ElementTree as ET
from pathlib import Path
from scripts.r23_io import *
SUITE=['tests/test_pre16_governance.py','tests/test_r21_promotion.py','tests/test_r22_contracts.py','tests/test_r22r1_contracts.py','tests/test_r23_runtime.py']
TAG='refs/tags/codex/r23-runtime-tested-source-20261004-r2'
def clean(source):
    assert subprocess.check_output(['git','rev-parse',TAG+'^{commit}'],cwd=ROOT,text=True).strip()==source
    from scripts.validate_r20_clean_detached import prepare_current,historical_representations
    directory,lfs=prepare_current(source)
    representations=historical_representations(directory,read('data/v4/V4_EXACT_BYTE_PORTABILITY_REGISTRY_R1.json'))
    before=subprocess.check_output(['git','status','--porcelain'],cwd=directory);assert before==b''
    env=dict(os.environ,PYTHONPATH='src'+os.pathsep+'.')
    cmd=[sys.executable,'-m','pytest',*SUITE,'-q','--junitxml='+str(ROOT/'reports/r23/clean_tests.xml')]
    result=subprocess.run(cmd,cwd=directory,env=env,capture_output=True,text=True,encoding='utf8',errors='replace')
    atomic('reports/r23/clean_runner.log',(result.stdout+result.stderr).encode(),raw=True)
    assert result.returncode==0,result.stdout+result.stderr
    after=subprocess.check_output(['git','status','--porcelain'],cwd=directory);assert before==after==b''
    cases=list(ET.parse(ROOT/'reports/r23/clean_tests.xml').iter('testcase'));assert len(cases)>=306 and not any(c.find(k) is not None for c in cases for k in ('failure','error','skipped'))
    # Verify the committed, persisted evidence independently in this exact checkout.
    from scripts import validate_r23_runtime as oracle
    database=read('reports/r23/INDEPENDENT_RUNTIME_ORACLE.json',directory)['database']['path']
    persisted=oracle.inspect_database(directory/database,directory);negative=oracle.negative_matrix(directory);oracle.protected(directory)
    gate=dict(status='PASS_LOCAL',source=source,immutable_tested_tag=TAG,checkout=str(directory),command=cmd,exit_code=0,passed=len(cases),failed=0,errors=0,skipped=0,deselected=0,git_status_before='',git_status_after='',verified_lfs_objects=lfs,registered_historical_representations=representations,persisted_evidence_oracle=persisted,negative_evidence_oracle=negative)
    atomic('reports/r23/CLEAN_REGRESSION.json',gate)
    files=['R22R1_EXTERNAL_ACCEPTANCE_BINDING','RUNTIME_COMPONENT_INVENTORY','STORAGE_SCHEMA_GATE','MIGRATION_ISOLATED_DB_GATE','SOURCE_RECEIPT_GATE','SLOT_RUNTIME_GATE','SHADOW_PRIOR_GATE','TRANSACTION_ATOMICITY_GATE','COHORT_ENROLLMENT_GATE','MEMBERSHIP_CAPTURE_GATE','SETTLEMENT_ORCHESTRATION_GATE','HEALTH_RECEIPT_GATE','LEGACY_ISOLATION_GATE','ROLLBACK_DRILL','POSITIVE_E2E_ENGINEERING','NEGATIVE_E2E_MATRIX','INDEPENDENT_RUNTIME_ORACLE','PROTECTED_BYTES','LOCAL_TEST_SUMMARY','CLEAN_REGRESSION']
    seal=dict(contract_id='R23_RUNTIME_CANDIDATE_SEAL',execution_baseline=BASE,tested_source=source,immutable_tested_tag=TAG,R22R1_EXTERNAL_ACCEPTANCE='FORMALIZED',V4_16_RUNTIME_ENGINEERING='PASS_LOCAL_READY_FOR_EXTERNAL_AUDIT',V4_16_RUNTIME_IMPLEMENTED='ENGINEERING_CANDIDATE_DISABLED',V4_16_RUNTIME_ACTIVATION='NOT_AUTHORIZED',REAL_SHADOW_OBSERVATIONS=0,PIT_OBSERVED_REAL_SAMPLES=0,SHADOW_STABLE='NOT_GRANTED',PROVISIONAL_FORWARD_EVIDENCE='NOT_GRANTED',FORWARD_SUPPORTED='NOT_GRANTED',V4_16_ACCEPTED_HEAD='NOT_CREATED',V4_STAGE_ACCEPTED_HEAD='V4_00_TO_V4_15_ACCEPTED',V4_DATA_ACCEPTED_HEAD='2026-09-30',HISTORICAL_PIT_EFFECTIVENESS='NOT_GRANTED',REAL_MATURED_ACCEPTED_SOURCE_SETTLEMENT_RUNTIME='NOT_GRANTED_PENDING_MATURITY_EVIDENCE',REALTIME_ACCEPTED_COHORT_MATURITY='NOT_GRANTED',production=False,shadow=False,focus=False,V4_16=False,NEXT='STOP_WAIT_R23_INDEPENDENT_EXTERNAL_AUDIT',bindings=[ref(p) for p in (ACCEPT,AUTH,DEPS,AUDIT,'migrations/v4_16_r23_shadow_v1.sql','scripts/v4_16_shadow_runtime.py','reports/r23/clean_tests.xml','reports/r23/clean_runner.log')]+[ref('reports/r23/'+n+'.json') for n in files])
    atomic('reports/r23/R23_RUNTIME_CANDIDATE_SEAL.json',seal)
    print(json.dumps(dict(source=source,checkout=str(directory),passed=len(cases),lfs_verified=len(lfs))))
if __name__=='__main__':clean(sys.argv[1])
