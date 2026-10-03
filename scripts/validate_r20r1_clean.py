"""Full relevant R20 current regression plus R20R1 in one exact detached source.

Historical R19/R17/R18 suites keep their prior audited contexts and are not rerun.
"""
import json,os,subprocess,sys,xml.etree.ElementTree as ET
from pathlib import Path
from scripts.validate_r20_clean_detached import prepare_current
from scripts.r20r1_io import ROOT,BASE,atomic,ref
def run(source):
    subprocess.run(['git','merge-base','--is-ancestor',BASE,source],cwd=ROOT,check=True)
    require_clean=subprocess.check_output(['git','diff',BASE,source,'--name-only','--','src','data','reports/r20a','reports/r20b','reports/r20c','reports/r20d','reports/r20e','reports/v4_15_runtime_r20'],cwd=ROOT)
    if require_clean:raise ValueError('PASS_KEEP_SOURCE_OR_EVIDENCE_CHANGED')
    directory,lfs=prepare_current(source)
    tests=sorted(str(p.relative_to(directory)).replace('\\','/') for p in (directory/'tests').glob('test_r20*.py'))
    if len(tests)!=6 or 'tests/test_r20r1_scope.py' not in tests:raise ValueError('ALL_CURRENT_SUITES_REQUIRED')
    out=ROOT/'reports/r20r1/clean_regression';out.mkdir(parents=True,exist_ok=True);xml=out/'tests.xml'
    before=subprocess.check_output(['git','status','--porcelain'],cwd=directory)
    command=[sys.executable,'-m','pytest',*tests,'-q','--junitxml='+str(xml)]
    result=subprocess.run(command,cwd=directory,capture_output=True,text=True,encoding='utf8',errors='replace')
    atomic('reports/r20r1/clean_regression/runner.log',(result.stdout+result.stderr).encode(),raw=True)
    after=subprocess.check_output(['git','status','--porcelain'],cwd=directory)
    if result.returncode or before or after:raise ValueError('CLEAN_REGRESSION_FAILED: '+str(out/'runner.log'))
    cases=list(ET.parse(xml).iter('testcase'))
    if any(c.find(k) is not None for c in cases for k in ['failure','error','skipped']):raise ValueError('NO_FAILURE_SKIP')
    new_count=sum(c.attrib.get('classname','').startswith('tests.test_r20r1_scope') or c.attrib.get('classname','').startswith('test_r20r1_scope') for c in cases)
    if len(cases)-new_count!=107 or new_count<51:raise ValueError('COMPLETE_PRIOR_R20_AND_NEW_SCOPE_REQUIRED')
    receipt=dict(status='PASS_LOCAL',execution_baseline=BASE,tested_source=source,checkout=str(directory),command=command,test_suites=tests,passed=len(cases),R20_current_passed=107,R20R1_passed=new_count,failures=0,errors=0,skipped=0,deselected=0,git_status_before='',git_status_after='',verified_LFS_objects=lfs,historical_regression='PASS_KEEP_NOT_RERUN;_1168_PLUS_62_PRIOR_AUDITED_CONTEXTS',prior_regression=ref('reports/r20e/clean_regression/CLEAN_DETACHED_REGRESSION.json'),accepted_algorithms_and_R20_runtime_unchanged=True)
    atomic('reports/r20r1/clean_regression/CLEAN_DETACHED_REGRESSION.json',receipt);print(json.dumps({'status':receipt['status'],'passed':len(cases),'checkout':str(directory)}))
if __name__=='__main__':run(sys.argv[1])
