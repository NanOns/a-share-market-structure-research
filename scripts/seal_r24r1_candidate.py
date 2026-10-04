"""Immutable source tag, clean full regression and evidence-only successor seal."""
import os, subprocess, sys
from scripts.r24r1_io import ROOT, BASE, read, ref, atomic
from scripts.validate_r20_clean_detached import prepare_current, historical_representations
from scripts.seal_r24_candidate import summary as old_summary, SUITES as OLD_SUITES
from scripts.validate_r24r1_activation import inspect, protected
from scripts.r24r1_protection import protected_bytes

SUITES=OLD_SUITES+['tests/test_r24r1_authority.py','tests/test_r24r1_a20.py']

def summary(path):
    result=old_summary(path); result['suites']=SUITES
    return result

def run(source,tag):
    assert subprocess.check_output(['git','rev-parse',tag],cwd=ROOT,text=True).strip()==source
    subprocess.run(['git','merge-base','--is-ancestor',BASE,source],cwd=ROOT,check=True)
    print('Preparing immutable clean detached source and exact LFS objects',flush=True)
    directory,lfs=prepare_current(source)
    representations=historical_representations(directory,read('data/v4/V4_EXACT_BYTE_PORTABILITY_REGISTRY_R1.json'))
    assert subprocess.check_output(['git','status','--porcelain'],cwd=directory)==b''
    print('Running all historical suites plus R24R1 authority and A01–A20',flush=True)
    xml=ROOT/'reports/r24r1/clean_tests.xml'
    cmd=[sys.executable,'-m','pytest',*SUITES,'-q','--junitxml='+str(xml)]
    result=subprocess.run(cmd,cwd=directory,env=dict(os.environ,PYTHONPATH='src'+os.pathsep+'.'),capture_output=True)
    atomic('reports/r24r1/clean_runner.log',result.stdout+result.stderr,raw=True)
    assert result.returncode==0,'CLEAN_REGRESSION_FAILED'
    assert b'deselected' not in result.stdout
    tests=summary(xml)
    assert subprocess.check_output(['git','status','--porcelain'],cwd=directory)==b''
    context=read('reports/r24r1/FUTURE_SESSION_REACHABILITY_GATE.json',directory)['context']
    oracle=inspect(directory/context['database'],context['manifest'],directory)
    protection=protected_bytes(directory)
    atomic('reports/r24r1/CLEAN_REGRESSION.json',dict(tests,status='PASS_LOCAL',tested_source=source,immutable_tag=tag,
        checkout=str(directory),git_status_before='',git_status_after='',verified_lfs_objects=lfs,
        registered_representations=representations,command=cmd,independent_oracle=oracle,protected=protection,no_broad_deselection=True))
    evidence=[ref('reports/r24r1/'+p.name) for p in sorted((ROOT/'reports/r24r1').glob('*.json')) if p.name!='R24R1_CANDIDATE_SEAL.json']
    seal=dict(status='PASS_LOCAL_READY_FOR_EXTERNAL_AUDIT',execution_baseline=BASE,tested_source=source,immutable_tag=tag,
        post_test_changes='EVIDENCE_ONLY',external_acceptance='NOT_GRANTED',
        V4_16_REAL_SHADOW_RUNTIME='FUTURE_SESSION_ACTIVATION_CAPABLE_DISABLED_CANDIDATE',
        runtime_authorized=False,real_shadow_authorized=False,grant=None,REAL_SHADOW_OBSERVATIONS=0,PIT_OBSERVED_REAL_SAMPLES=0,
        Stage='V4_00_TO_V4_15_ACCEPTED',Data='2026-09-30',V4_16_ACCEPTED_HEAD='NOT_CREATED',Production=False,Shadow=False,Focus=False,V4_16=False,
        NEXT='STOP_WAIT_R24R1_INDEPENDENT_EXTERNAL_AUDIT',evidence=evidence)
    seal.update(R24R1_FORWARD_DAILY_INPUT_AUTHORITY=seal['status'],R24R1_COHORT_IDENTITY=seal['status'],
        R24R1_REALTIME_ADMISSION=seal['status'],REAL_SHADOW_RUNTIME=seal['V4_16_REAL_SHADOW_RUNTIME'])
    atomic('reports/r24r1/R24R1_CANDIDATE_SEAL.json',seal)
    print(dict(status=seal['status'],passed=tests['passed'],tested_source=source),flush=True)

if __name__=='__main__':run(*sys.argv[1:])
