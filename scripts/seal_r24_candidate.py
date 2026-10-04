"""Immutable source, clean detached regression and evidence-only R24 seal."""
import os, subprocess, sys, xml.etree.ElementTree as ET
from scripts.r24_io import ROOT, BASE, read, ref, atomic
from scripts.validate_r20_clean_detached import prepare_current, historical_representations
from scripts.validate_r24_activation import inspect, protected
SUITES=['tests/test_pre16_governance.py','tests/test_r21_promotion.py','tests/test_r22_contracts.py',
        'tests/test_r22r1_contracts.py','tests/test_r23_runtime.py','tests/test_r23r1_runtime.py','tests/test_r24_activation.py']

def summary(path):
    cases=list(ET.parse(path).iter('testcase'))
    assert cases and not any(c.find(k) is not None for c in cases for k in ('failure','error','skipped'))
    return dict(passed=len(cases),failures=0,errors=0,skipped=0,deselected=0,suites=SUITES)

def run(source,tag):
    assert subprocess.check_output(['git','rev-parse',tag],cwd=ROOT,text=True).strip()==source
    subprocess.run(['git','merge-base','--is-ancestor',BASE,source],cwd=ROOT,check=True)
    print('Preparing exact clean detached source and verifying registered LFS bytes',flush=True)
    directory,lfs=prepare_current(source)
    representations=historical_representations(directory,read('data/v4/V4_EXACT_BYTE_PORTABILITY_REGISTRY_R1.json'))
    assert subprocess.check_output(['git','status','--porcelain'],cwd=directory)==b''
    print('Running seven complete stage regression suites',flush=True)
    xml=ROOT/'reports/r24/clean_tests.xml'
    cmd=[sys.executable,'-m','pytest',*SUITES,'-q','--junitxml='+str(xml)]
    result=subprocess.run(cmd,cwd=directory,env=dict(os.environ,PYTHONPATH='src'+os.pathsep+'.'),capture_output=True)
    atomic('reports/r24/clean_runner.log',result.stdout+result.stderr,raw=True)
    assert result.returncode==0,'CLEAN_REGRESSION_FAILED'
    assert b'deselected' not in result.stdout
    tests=summary(xml)
    assert subprocess.check_output(['git','status','--porcelain'],cwd=directory)==b''
    context=read('reports/r24/ACTIVATION_SIMULATION_E2E.json',directory)['context']
    oracle=inspect(directory/context['database'],context['manifest'],directory)
    protection=protected(directory)
    receipt=dict(tests,status='PASS_LOCAL',tested_source=source,immutable_tag=tag,checkout=str(directory),
      git_status_before='',git_status_after='',verified_lfs_objects=lfs,registered_representations=representations,
      command=cmd,independent_oracle=oracle,protected=protection,no_broad_deselection=True)
    atomic('reports/r24/CLEAN_REGRESSION.json',receipt)
    evidence=[ref('reports/r24/'+p.name) for p in sorted((ROOT/'reports/r24').glob('*.json')) if p.name!='R24_CANDIDATE_SEAL.json']
    seal=dict(status='PASS_LOCAL_READY_FOR_EXTERNAL_AUDIT',execution_baseline=BASE,tested_source=source,
       immutable_tag=tag,post_test_changes='EVIDENCE_ONLY',external_acceptance='NOT_GRANTED',
       R24_REAL_SHADOW_ACTIVATION_READINESS='PASS_LOCAL_READY_FOR_EXTERNAL_AUDIT',
       REAL_SHADOW_RUNTIME='ACTIVATION_CAPABLE_DISABLED_CANDIDATE',runtime_authorized=False,
       V4_16_REAL_SHADOW_RUNTIME='ACTIVATION_CAPABLE_DISABLED_CANDIDATE',
       V4_16_REAL_SHADOW_ACTIVATION='NOT_AUTHORIZED',
       real_shadow_authorized=False,REAL_SHADOW_OBSERVATIONS=0,PIT_OBSERVED_REAL_SAMPLES=0,
       Stage='V4_00_TO_V4_15_ACCEPTED',Data='2026-09-30',V4_16_ACCEPTED_HEAD='NOT_CREATED',
       Production=False,Shadow=False,Focus=False,V4_16=False,
       NEXT='STOP_WAIT_R24_INDEPENDENT_EXTERNAL_AUDIT',evidence=evidence)
    atomic('reports/r24/R24_CANDIDATE_SEAL.json',seal)
    print(dict(status=seal['status'],tested_source=source,passed=tests['passed']),flush=True)

if __name__=='__main__':run(*sys.argv[1:])
