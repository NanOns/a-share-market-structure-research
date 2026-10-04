"""Clean detached governance regression; explicit immutable source, verified LFS."""
import json,subprocess,sys,os
import xml.etree.ElementTree as ET
from pathlib import Path
from scripts.pre16_governance_io import ROOT,BASE,atomic,ref
from scripts.validate_r20_clean_detached import prepare_current,historical_representations

def run(source):
    resolved=subprocess.check_output(['git','rev-parse',source+'^{commit}'],cwd=ROOT).decode().strip()
    if resolved!=source:raise ValueError('FULL_IMMUTABLE_SOURCE_REQUIRED')
    subprocess.check_call(['git','merge-base','--is-ancestor',BASE,source],cwd=ROOT)
    directory,lfs=prepare_current(source)
    representations=historical_representations(directory,json.loads((ROOT/'data/v4/V4_EXACT_BYTE_PORTABILITY_REGISTRY_R1.json').read_bytes()))
    before=subprocess.check_output(['git','status','--porcelain'],cwd=directory)
    xml=ROOT/'reports/pre16_governance/clean_tests.xml'
    command=[sys.executable,'-m','pytest','tests/test_pre16_governance.py','tests/test_r21_promotion.py','-q','--junitxml='+str(xml)]
    env=dict(os.environ,PYTHONPATH='src'+os.pathsep+'.')
    result=subprocess.run(command,cwd=directory,capture_output=True,env=env)
    atomic('reports/pre16_governance/clean_runner.log',result.stdout+result.stderr,raw=True)
    after=subprocess.check_output(['git','status','--porcelain'],cwd=directory)
    assert before==after==b'','CLEAN_CONTEXT_CHANGED'
    assert result.returncode==0,'CLEAN_REGRESSION_FAILED'
    cases=list(ET.parse(xml).iter('testcase'))
    assert cases and not any(c.find(k) is not None for c in cases for k in ['failure','error','skipped'])
    assert b'deselected' not in result.stdout
    gate=dict(contract_id='PRE16_CLEAN_GOVERNANCE_REGRESSION_V1',status='PASS_LOCAL',tested_source=source,baseline=BASE,checkout=str(directory),detached=True,git_status_before='',git_status_after='',command=command,passed=len(cases),failed=0,errors=0,skipped=0,deselected=0,scope='PRE16 governance and exact R21 promotion/current-stage/replay/rollback; accepted business stages remain unchanged',verified_lfs_objects=lfs,registered_historical_representations=representations,test_results=ref('reports/pre16_governance/clean_tests.xml'),runner=ref('reports/pre16_governance/clean_runner.log'),business_source_changes=subprocess.check_output(['git','diff',BASE,source,'--name-only','--','src'],cwd=ROOT).decode().splitlines())
    assert gate['business_source_changes']==[]
    atomic('reports/pre16_governance/CLEAN_GOVERNANCE_REGRESSION.json',gate)
    print(json.dumps({k:gate[k] for k in ['status','tested_source','passed','checkout']}))
if __name__=='__main__':run(sys.argv[1])
