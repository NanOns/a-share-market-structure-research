"""Exact detached R21 source plus unchanged historical tests in archived Stage14."""
import json,subprocess,sys,xml.etree.ElementTree as ET
from pathlib import Path
from scripts.r21_io import ROOT,BASE,atomic,ref
from scripts.validate_r20_clean_detached import prepare_current
def run_suite(directory,command,out):
    out.mkdir(parents=True,exist_ok=True)
    before=subprocess.check_output(['git','status','--porcelain'],cwd=directory)
    r=subprocess.run(command,cwd=directory,capture_output=True,text=True,encoding='utf8',errors='replace')
    atomic((out/ 'runner.log').relative_to(ROOT).as_posix(),(r.stdout+r.stderr).encode(),raw=True)
    after=subprocess.check_output(['git','status','--porcelain'],cwd=directory)
    assert before==after==b'','DETACHED_SOURCE_CHANGED'
    assert r.returncode==0,str(out/'runner.log')
    cases=list(ET.parse(out/'tests.xml').iter('testcase'))
    assert not any(c.find(k) is not None for c in cases for k in ['failure','error','skipped'])
    return dict(source=subprocess.check_output(['git','rev-parse','HEAD'],cwd=directory).decode().strip(),checkout=str(directory),command=command,passed=len(cases),failures=0,errors=0,skipped=0,git_status_before='',git_status_after='',xml=ref((out/'tests.xml').relative_to(ROOT).as_posix()),runner=ref((out/'runner.log').relative_to(ROOT).as_posix()))
def run(source):
    directory,lfs=prepare_current(source)
    out=ROOT/'reports/r21/clean_regression/current'
    tests=sorted(p.relative_to(directory).as_posix() for p in (directory/'tests').glob('test_r20*.py'))+['tests/test_r21_promotion.py']
    registry=json.loads((ROOT/'reports/r21/SUPERSEDED_CURRENT_STAGE_TESTS.json').read_bytes());nodes=[e['nodeid'] for e in registry['entries']]
    current=run_suite(directory,[sys.executable,'-m','pytest','-p','scripts.r21_scoped_pytest',*tests,'-q','--junitxml='+str(out/'tests.xml')],out)
    assert current['passed']==231-len(nodes)+20,current
    assert '55 deselected' in (out/'runner.log').read_text()
    archived,old_lfs=prepare_current(BASE)
    out=ROOT/'reports/r21/clean_regression/historical_current'
    code="import json,pytest,sys; r=json.load(open(sys.argv[1],encoding='utf8'));sys.exit(pytest.main([e['nodeid'] for e in r['entries']]+['-q','--junitxml='+sys.argv[2]]))"
    historical=run_suite(archived,[sys.executable,'-c',code,str(ROOT/'reports/r21/SUPERSEDED_CURRENT_STAGE_TESTS.json'),str(out/'tests.xml')],out)
    assert historical['passed']==len(nodes)
    assert 'deselected' not in (out/'runner.log').read_text()
    result=dict(status='PASS_LOCAL',tested_source=source,current=current,historical_current=historical,registered_exact_nodeids=nodes,total_passed=current['passed']+historical['passed'],current_stage_registered_superseded=len(nodes),historical_registered_cases_all_passed=True,unrelated_exclusions=0,verified_lfs_objects=lfs,historical_verified_lfs_objects=old_lfs)
    atomic('reports/r21/clean_regression/CLEAN_DETACHED_REGRESSION.json',result)
    print(json.dumps({k:v for k,v in result.items() if k not in ['verified_lfs_objects','historical_verified_lfs_objects','registered_exact_nodeids']}))
if __name__=='__main__':run(sys.argv[1])
