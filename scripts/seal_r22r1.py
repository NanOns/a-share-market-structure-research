"""Exact detached regression and evidence-only R22R1 candidate seal."""
import os,sys,subprocess,json
from pathlib import Path
import xml.etree.ElementTree as ET
from scripts.r22r1_io import *
SUITE=['tests/test_pre16_governance.py','tests/test_r21_promotion.py','tests/test_r22_contracts.py','tests/test_r22r1_contracts.py']
TAG='refs/tags/codex/r22r1-clock-tested-source-20261004-r1'
def summary(xml):
    cases=list(ET.parse(xml).iter('testcase'))
    result=dict(passed=len(cases),failed=sum(c.find('failure') is not None for c in cases),errors=sum(c.find('error') is not None for c in cases),skipped=sum(c.find('skipped') is not None for c in cases),deselected=0)
    assert result['passed']>=199 and not any(result[k] for k in ('failed','errors','skipped'))
    return result
def local():
    atomic('reports/r22r1/LOCAL_TEST_SUMMARY.json',dict(status='PASS_LOCAL',suite=SUITE,**summary(ROOT/'reports/r22r1/local_tests.xml')))
def clean(source):
    assert subprocess.check_output(['git','rev-parse',TAG+'^{commit}'],text=True,cwd=ROOT).strip()==source
    from scripts.validate_r20_clean_detached import prepare_current,historical_representations
    directory,lfs=prepare_current(source)
    representations=historical_representations(directory,read('data/v4/V4_EXACT_BYTE_PORTABILITY_REGISTRY_R1.json'))
    before=subprocess.check_output(['git','status','--porcelain'],cwd=directory);assert before==b''
    env=dict(os.environ,PYTHONPATH='src'+os.pathsep+'.')
    cmd=[sys.executable,'-m','pytest',*SUITE,'-q','--junitxml='+str(ROOT/'reports/r22r1/clean_tests.xml')]
    result=subprocess.run(cmd,cwd=directory,env=env,capture_output=True,text=True,encoding='utf8',errors='replace')
    atomic('reports/r22r1/clean_runner.log',(result.stdout+result.stderr).encode(),raw=True)
    assert result.returncode==0,result.stdout+result.stderr
    after=subprocess.check_output(['git','status','--porcelain'],cwd=directory);assert before==after==b''
    gate=dict(status='PASS_LOCAL',source=source,immutable_tested_tag=TAG,checkout=str(directory),command=cmd,exit_code=0,git_status_before='',git_status_after='',verified_lfs_objects=lfs,registered_historical_representations=representations,**summary(ROOT/'reports/r22r1/clean_tests.xml'))
    atomic('reports/r22r1/CLEAN_REGRESSION.json',gate)
    from scripts.validate_r22r1_contracts import validate
    validate()
    seal=dict(contract_id='R22R1_CANDIDATE_SEAL',execution_baseline=BASE,tested_source=source,immutable_tested_tag=TAG,tested_source_must_be_remote_ancestor=True,R22R1_CLOCK_AUTHORITY='PASS_LOCAL_READY_FOR_EXTERNAL_AUDIT',V4_16_CONTRACT_ACCEPTANCE='FORMALIZED_CONTRACT_ONLY',CLOCK_POLICY='21:00 / 22:30 Asia/Shanghai',V4_16_OBSERVATION_SLOT_V2='CLOCK_BOUND_CANDIDATE',PRE16_CURRENT_AUDIT_AUTHORITY='V3_NORMALIZED_CANDIDATE',V4_16_RUNTIME='NOT_AUTHORIZED',REAL_SHADOW_OBSERVATIONS=0,V4_STAGE_ACCEPTED_HEAD='V4_00_TO_V4_15_ACCEPTED',V4_DATA_ACCEPTED_HEAD='2026-09-30',V4_16_ACCEPTED_HEAD='NOT_CREATED',HISTORICAL_PIT_EFFECTIVENESS='NOT_GRANTED',production=False,shadow=False,focus=False,V4_16=False,NEXT='STOP_WAIT_R22R1_INDEPENDENT_EXTERNAL_AUDIT',bindings=[ref(p) for p in (ACCEPT,CLOCK,SLOT,HEAD,CONFIG,VECTORS,'reports/r22r1/CLEAN_REGRESSION.json','reports/r22r1/LOCAL_TEST_SUMMARY.json','reports/r22r1/R22_EXTERNAL_ACCEPTANCE_BINDING.json','reports/r22r1/CLOCK_POLICY_GATE.json','reports/r22r1/SOURCE_VISIBILITY_TIME_GATE.json','reports/r22r1/CLOCK_MACHINE_VECTORS.json','reports/r22r1/PRE16_V3_NORMALIZATION_GATE.json','reports/r22r1/PROTECTED_BYTES.json')])
    atomic('reports/r22r1/R22R1_CANDIDATE_SEAL.json',seal)
    print(json.dumps(dict(source=source,checkout=str(directory),passed=gate['passed'],lfs_verified=len(lfs))))
if __name__=='__main__':
    if len(sys.argv)==1:local()
    else:clean(sys.argv[1])
