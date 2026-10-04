"""Exact detached regression and evidence-only disabled candidate seal."""
import os,subprocess,sys,xml.etree.ElementTree as ET
from pathlib import Path
from scripts.r23r1_io import *
from scripts.validate_r20_clean_detached import prepare_current,historical_representations
from scripts.validate_r23r1_runtime import inspect_database,protected
SUITES=['tests/test_pre16_governance.py','tests/test_r21_promotion.py','tests/test_r22_contracts.py','tests/test_r22r1_contracts.py','tests/test_r23_runtime.py','tests/test_r23r1_runtime.py']
def xml_summary(path):
    cases=list(ET.parse(path).iter('testcase'))
    assert cases and not any(c.find(k) is not None for c in cases for k in ('failure','error','skipped'))
    return dict(passed=len(cases),failures=0,errors=0,skipped=0,deselected=0,suites=SUITES)
def run(source,tag):
    assert subprocess.check_output(['git','rev-parse',tag],cwd=ROOT,text=True).strip()==source
    assert subprocess.run(['git','merge-base','--is-ancestor',BASE,source],cwd=ROOT).returncode==0
    print('Preparing exact detached source and verifying LFS bytes',flush=True)
    directory,lfs=prepare_current(source)
    representations=historical_representations(directory,read('data/v4/V4_EXACT_BYTE_PORTABILITY_REGISTRY_R1.json'))
    assert subprocess.check_output(['git','status','--porcelain'],cwd=directory)==b''
    print('Running all six suites in detached checkout',flush=True)
    xml=ROOT/'reports/r23r1/clean_tests.xml'
    cmd=[sys.executable,'-m','pytest',*SUITES,'-q','--junitxml='+str(xml)]
    environment=dict(os.environ,PYTHONPATH='src'+os.pathsep+'.')
    result=subprocess.run(cmd,cwd=directory,env=environment,capture_output=True)
    atomic('reports/r23r1/clean_runner.log',result.stdout+result.stderr,raw=True)
    assert result.returncode==0,'CLEAN_REGRESSION_FAILED'
    assert b'deselected' not in result.stdout
    summary=xml_summary(xml)
    assert subprocess.check_output(['git','status','--porcelain'],cwd=directory)==b''
    oracle=inspect_database(directory/'reports/r23r1/persisted/positive.sqlite',directory)
    negative=[]
    for n in range(25,33):
        path='reports/r23r1/persisted/N%02d.sqlite'%n
        item=read('reports/r23r1/persisted/N%02d.json'%n,directory)
        assert ref(path,directory)==item['database_binding']
        try:inspect_database(directory/path,directory)
        except ValueError as error:assert str(error)==item['rejection'];negative.append(item)
        else:raise AssertionError('NEGATIVE_NOT_REJECTED')
    protection=protected(directory)
    receipt=dict(summary,status='PASS_LOCAL',tested_source=source,immutable_tag=tag,checkout=str(directory),git_status_before='',git_status_after='',verified_lfs_objects=lfs,registered_representations=representations,command=cmd,independent_oracle=oracle,negative_cases=negative,protected=protection,no_broad_deselection=True)
    atomic('reports/r23r1/CLEAN_REGRESSION.json',receipt)
    evidence=[ref(p.relative_to(ROOT).as_posix()) for p in sorted((ROOT/'reports/r23r1').glob('*.json')) if p.name!='R23R1_CANDIDATE_SEAL.json']
    seal=dict(status='PASS_LOCAL_READY_FOR_EXTERNAL_AUDIT',execution_baseline=BASE,tested_source=source,immutable_tag=tag,post_test_changes='EVIDENCE_ONLY',external_acceptance='NOT_GRANTED',R23R1_SLOT_RUNTIME_COMPLETENESS='PASS_LOCAL_READY_FOR_EXTERNAL_AUDIT',R23_RUNTIME_ENGINEERING='PASS_LOCAL_READY_FOR_EXTERNAL_AUDIT',R23_RUNTIME_IMPLEMENTED='ENGINEERING_CANDIDATE_DISABLED',V4_16_RUNTIME_ACTIVATION='NOT_AUTHORIZED',runtime_authorized=False,real_shadow_authorized=False,REAL_SHADOW_OBSERVATIONS=0,PIT_OBSERVED_REAL_SAMPLES=0,V4_STAGE_ACCEPTED_HEAD='V4_00_TO_V4_15_ACCEPTED',V4_DATA_ACCEPTED_HEAD='2026-09-30',Production=False,Shadow=False,Focus=False,V4_16=False,V4_16_ACCEPTED_HEAD='NOT_CREATED',NEXT='STOP_WAIT_R23R1_INDEPENDENT_EXTERNAL_AUDIT',evidence=evidence)
    atomic('reports/r23r1/R23R1_CANDIDATE_SEAL.json',seal)
    print(dict(tested_source=source,passed=summary['passed'],checkout=str(directory),status=seal['status']),flush=True)
if __name__=='__main__':run(*sys.argv[1:])
