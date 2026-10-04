"""Seal an exact tested source plus evidence-only closure; no acceptance grant."""
import argparse
import hashlib
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET
from run_regression import ROOT,atomic
from build_evidence import read,ref,protected

TAG='codex/r26-shadow-ui-tested-source-20261004-r2'


def git(args,cwd=ROOT):return subprocess.check_output(['git',*args],cwd=cwd)


def seal(source,directory,lfs):
    directory=Path(directory).resolve()
    assert directory.drive.upper() in ('E:','F:')
    assert git(['rev-parse','HEAD'],directory).decode().strip()==source
    assert git(['status','--porcelain'],directory)==b''
    current=read('reports/r26/clean-summary.json');baseline=read('reports/r26/baseline-final-summary.json')
    assert current['source_commit']==source and current['tests']==221 and current['passed']==218
    assert current['errors']==current['skipped']==current['deselected']==0
    assert {(x['node'],x['message']) for x in current['failures']}=={(x['node'],x['message']) for x in baseline['failures']}
    tree=ET.parse(ROOT/current['xml']);new=[t for t in tree.findall('.//testcase') if 'test_v4_17_shadow_ui' in t.get('classname','')]
    assert len(new)==44 and all(t.find('failure') is None and t.find('error') is None and t.find('skipped') is None for t in new)
    state=protected()
    saved=read('reports/r26/UNRELATED_WORKTREE_PRESERVATION.json')
    for item in saved['entries']:
        path=ROOT/item['path']
        with path.open('rb') as stream:assert hashlib.file_digest(stream,'sha256').hexdigest()==item['sha256'],item['path']
    assert len(lfs)==171
    atomic('reports/r26/CLEAN_REGRESSION.json',dict(status='PASS_SCOPED_NO_NEW_FAILURES',tested_source=source,tested_source_ref='refs/tags/'+TAG,
                directory=str(directory),clean_before=True,clean_after=True,tests=221,passed=218,R26_feature_passed=44,R26_feature_failed=0,
                inherited_failures=current['failures'],new_failures=[],errors=0,skipped=0,deselected=0,actual_pytest_exit_code=1,
                audit_item='R26-A01_OPEN_INDEPENDENT',test_summary=ref('reports/r26/clean-summary.json'),test_xml=ref(current['xml']),
                temporary_root='E:/codex_tmp/test_temp',LFS_exact_object_and_checkout_proof=lfs,not_zero_failure_comprehensive_suite=True))
    for path in ('config/v4_17_shadow_ui_contract_v1.json','config/v4_17_shadow_ui_source_v1.json',
                 'src/workbench_service/app.py','src/workbench_service/shadow_context.py','src/workbench_service/static/shadow-v4.html',
                 'src/workbench_service/static/shadow-v4.js','tests/test_v4_17_shadow_ui.py'):
        assert git(['show',source+':'+path])==(ROOT/path).read_bytes(),path
    artifacts=[]
    for prefix in ('reports/r26','docs/evidence/r26'):
        for path in sorted((ROOT/prefix).rglob('*')):
            if not path.is_file() or '__pycache__' in path.parts or path.suffix=='.pyc' or path.name=='R26_CANDIDATE_SEAL.json':continue
            assert not path.name.endswith(('staging','.tmp'))
            artifacts.append(ref(path.relative_to(ROOT).as_posix()))
    atomic('reports/r26/R26_CANDIDATE_SEAL.json',dict(contract_id='R26_SHADOW_UI_ENGINEERING_CANDIDATE_SEAL_V1',baseline=state['baseline'],tested_source=source,
                tested_source_ref='refs/tags/'+TAG,source_tree=git(['rev-parse',source+'^{tree}']).decode().strip(),closure_policy='EVIDENCE_ONLY_AFTER_TESTED_SOURCE',
                V4_17_ENGINEERING='PASS_LOCAL_READY_FOR_EXTERNAL_AUDIT',V4_17_REAL_SHADOW_READBACK='NOT_GRANTED_NO_REAL_PUBLICATION',
                V4_17_FINAL_ACCEPTANCE='NOT_GRANTED',V4_17G='NOT_GRANTED',R25_REAL_ACTIVATION_PACKET='WAIT_ACCEPTED_DAILY_INPUT',
                REAL_SHADOW_EXECUTION='NOT_STARTED',REAL_SHADOW_OBSERVATIONS=0,PIT_OBSERVED_REAL_SAMPLES=0,
                Production=False,Focus_source_cutover=False,NEXT='STOP_WAIT_R26_INDEPENDENT_EXTERNAL_AUDIT',
                R26_feature_tests='44_PASS',existing_regression='174_PASS_3_INHERITED_FAILURES_NO_NEW_FAILURES',audit_item='R26-A01_OPEN_INDEPENDENT',
                protected_baseline_file_count=state['count'],unrelated_worktree_preserved=True,artifacts=artifacts,git_push_is_external_acceptance=False))
    print('PASS_R26_LOCAL_CANDIDATE_SEALED_WAIT_EXTERNAL_AUDIT',source,flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--source',required=True);parser.add_argument('--directory',required=True);args=parser.parse_args()
    seal(args.source,args.directory,read('reports/r26/clean-worktree.json')['lfs'])
