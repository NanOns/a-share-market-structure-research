"""Complete current R20/R20R1/R20R1R1/R20R1R2 suites in an exact detached source."""
import json,re,sys,subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from scripts.validate_r20_clean_detached import prepare_current,suite
from scripts.r20r1r2_io import ROOT,BASE,atomic

def run(source):
    protected=['src','data','reports/r20a','reports/r20b','reports/r20c','reports/r20d','reports/r20e','reports/v4_15_runtime_r20','reports/r20r1','reports/r20r1r1']
    assert subprocess.check_output(['git','diff',BASE,source,'--name-only','--',*protected],cwd=ROOT)==b''
    directory,lfs=prepare_current(source)
    out=ROOT/'reports/r20r1r2/clean_regression';out.mkdir(parents=True,exist_ok=True)
    tests=sorted(p.relative_to(directory).as_posix() for p in (directory/'tests').glob('test_r20*.py'))
    assert len(tests)==8,tests
    xml=out/'tests.xml'
    result=suite(directory,[sys.executable,'-m','pytest',*tests,'-q','--junitxml='+str(xml)],out)
    cases=list(ET.parse(xml).iter('testcase'))
    assert not any(c.find(k) is not None for c in cases for k in ['failure','error','skipped'])
    assert not re.search(r'\b[1-9]\d* deselected\b',(out/'runner.log').read_text())
    counts={}
    for c in cases:
        name=c.attrib['classname'];counts[name]=counts.get(name,0)+1
    assert counts['tests.test_r20r1_scope']==51 and counts['tests.test_r20r1r1_maturity']==35 and counts['tests.test_r20r1r2_dm01']==38
    assert sum(v for k,v in counts.items() if k not in ['tests.test_r20r1_scope','tests.test_r20r1r1_maturity','tests.test_r20r1r2_dm01'])==107
    result.update(status='PASS_LOCAL',tested_source=source,scope='ALL_R20_CURRENT_AND_ALL_R20R1_AND_ALL_R20R1R1_AND_ALL_R20R1R2_NO_DESELECTION',passed=len(cases),suite_counts=counts,failures=0,errors=0,skipped=0,deselected=0,verified_lfs_objects=lfs,protected_sources_and_prior_evidence_unchanged=True,checkout=str(directory))
    atomic('reports/r20r1r2/clean_regression/CLEAN_DETACHED_REGRESSION.json',result)
    print(json.dumps({k:v for k,v in result.items() if k!='verified_lfs_objects'}))
if __name__=='__main__':run(sys.argv[1])
