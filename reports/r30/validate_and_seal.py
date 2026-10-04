"""Read-only R30 contract/vector checks and E-drive exact-source evidence."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from reports.r30.build_contract import BASE,sha,write
from reports.r30.design_ledger import vector_result


def protected():
    b=json.loads((ROOT/'reports/r30/PROTECTED_BASELINE.json').read_text(encoding='utf8'))
    changed=[n for n,d in b['tracked'].items() if not (ROOT/n).is_file() or sha(ROOT/n)!=d]
    unrelated=[n for n,d in b['unrelated'].items() if not (ROOT/n).is_file() or sha(ROOT/n)!=d]
    result=dict(baseline=BASE,tracked_count=len(b['tracked']),unrelated_count=len(b['unrelated']),changed=changed,unrelated_changed=unrelated,status='PASS' if not changed and not unrelated else 'FAIL',production_databases_opened=False,tdx_writes=False,actual_real_observations_written=0,settlement_owner_changed=False,actual_ui_focus_route_changed=False)
    write('reports/r30/PROTECTED_BYTES.json',result); assert result['status']=='PASS',result
    return result


def static_oracle():
    c=json.loads((ROOT/'config/v4_21_continued_forward_observation_contract_v1.json').read_text(encoding='utf8')); results={}
    for i,vector in enumerate(c['vectors'],1):
        actual=vector_result(i)
        assert actual['status']==vector['expected_status'] and actual['actual_real_rows_written']==0 and actual['production_grant'] is False
        results[vector['id']]=dict(actual=actual,expected_status=vector['expected_status'],status='PASS_DESIGN_SIMULATION_ONLY',independent_assertions='tests/test_v4_21_forward_observation_contract.py::test_twenty_design_vectors')
    write('reports/r30/DESIGN_VECTOR_RESULTS.json',dict(scope='SYNTHETIC_DESIGN_NOT_REAL_FORWARD_EVIDENCE',results=results))
    for owner in c['owner_bindings']: assert sha(ROOT/owner['path'])==owner['sha256']


def regression(directory,label):
    from reports.r26.run_regression import scope
    directory=Path(directory).resolve(); assert directory.drive.upper() in ('E:','F:')
    temp=Path('E:/codex_tmp/test_temp')/('r30-'+label)
    env=dict(os.environ,TEMP=str(temp.parent),TMP=str(temp.parent),TMPDIR=str(temp.parent),PYTHONDONTWRITEBYTECODE='1',PYTHONPATH='src'+os.pathsep+'.',PYTHONIOENCODING='utf-8',WORKBENCH_API_BACKEND='duckdb',WORKBENCH_PG_DSN='dbname=r30_mock host=127.0.0.1 port=1 connect_timeout=1')
    names=scope()+['tests/test_v4_17_shadow_ui.py','tests/test_v4_18_migration_contract.py','tests/test_v4_19_focus_cutover_contract.py','tests/test_v4_20_default_ui_contract.py','tests/test_v4_21_forward_observation_contract.py']
    capture=temp.parent/('r30-'+label+'.xml')
    result=subprocess.run([sys.executable,'-m','pytest',*names,'-q','--basetemp='+str(temp),'--junitxml='+str(capture)],cwd=directory,env=env,capture_output=True)
    raw=capture.read_bytes(); prefix='reports/r30/'+label
    write(prefix+'-tests.xml',raw.decode('utf8')); write(prefix+'-output.txt',(result.stdout+result.stderr).decode('utf8'))
    tree=ET.fromstring(raw); cases=tree.findall('.//testcase'); failures=[t.get('classname')+'::'+t.get('name') for t in cases if t.find('failure') is not None]
    debt={'tests.upgrade_v3.test_v3_unified_entry::test_v3_is_the_single_unified_workbench_entry','tests.upgrade_v3.test_p01_01_lock_scope::test_hot_rank_route_skips_request_scope','tests.upgrade_v3.test_p01_01_lock_scope::test_send_marks_disconnected_client_closed'}
    errors=len(tree.findall('.//error')); skipped=len(tree.findall('.//skipped'))
    s=dict(directory=str(directory),source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=directory,text=True).strip(),scope=names,tests=len(cases),passed=len(cases)-len(failures)-errors-skipped,failures=failures,errors=errors,skipped=skipped,deselected=0,exit_code=result.returncode,temporary_directory=str(temp),captured_xml_sha256=hashlib.sha256(raw).hexdigest(),captured_output_sha256=hashlib.sha256(result.stdout+result.stderr).hexdigest(),status='PASS_SCOPED_NO_NEW_FAILURES' if set(failures)==debt and errors==skipped==0 else 'FAIL',historical_debt='R26_A01_OPEN_NONBLOCKING_EXTERNAL_R26_TO_R29; NO_TEST_WEAKENING_OR_DESELECTION')
    write(prefix+'-summary.json',s); print(json.dumps({k:v for k,v in s.items() if k!='scope'},ensure_ascii=False),flush=True); assert s['status']=='PASS_SCOPED_NO_NEW_FAILURES',s


def seal(source):
    p=protected(); static_oracle()
    c=json.loads((ROOT/'config/v4_21_continued_forward_observation_contract_v1.json').read_text(encoding='utf8')); bindings={}
    for path in sorted((ROOT/'reports/r30').glob('*.json')):
        value=json.loads(path.read_text(encoding='utf8'))
        if 'section' in value:
            assert value['definition']==c[value['section']] and value['contract_sha256']==sha(ROOT/'config/v4_21_continued_forward_observation_contract_v1.json')
            bindings[path.name]='EXACT_SECTION_AND_SHA256'
    assert len(bindings)==11
    local=json.loads((ROOT/'reports/r30/local-summary.json').read_text(encoding='utf8')); clean=json.loads((ROOT/'reports/r30/clean-summary.json').read_text(encoding='utf8'))
    assert clean['source_commit']==source and clean['tests']==local['tests']==333
    write('reports/r30/LOCAL_TEST_SUMMARY.json',local); write('reports/r30/CLEAN_REGRESSION.json',clean)
    write('reports/r30/FORWARD_OBSERVATION_CONTRACT_GATE.json',dict(status='PASS_LOCAL_READY_FOR_EXTERNAL_AUDIT',scope='CONTINUED_FORWARD_OBSERVATION_CONTRACT_DESIGN_ONLY',bindings=bindings,evidence_lanes=5,capabilities=5,design_vectors=20,protected=p['status'],implementation_entry='BLOCKED_WAIT_REAL_OBSERVATION',REAL_CONTINUED_FORWARD_OBSERVATION='NOT_STARTED',V4_21_ACCEPTED_HEAD='NOT_CREATED',next_stage=c['next_stage']))
    write('reports/r30/AUDIT_ITEM_CARRY.json',dict(item='R26_A01_INHERITED_V3_REGRESSION',scope='V3 unified-entry source literal and two _NoopService status mocks',evidence=['reports/r30/clean-tests.xml','docs/evidence/r30/V4_R29_V4_20_DEFAULT_UI_CUTOVER_CONTRACT_DESIGN_FINAL_INDEPENDENT_EXTERNAL_AUDIT_R1_20261004.md'],acceptance='OPEN_NONBLOCKING_HISTORICAL_DEBT; SEPARATE_REPAIR_AND_ACCEPTANCE_REQUIRED',r30='NO_AUTOMATIC_CLOSURE',R28_P2='CLOSED_BY_EXTERNAL_R29_AUDIT_CARRIED_WITHOUT_REOPENING'))
    write('docs/evidence/r30/R30_CONTRACT_DESIGN_ACCEPTANCE.md','# R30 V4-21 Continued Forward Observation contract design\n\nBaseline: `'+BASE+'`. Exact tested source: `'+source+'`.\n\nThis candidate freezes evidence accumulation/readback only. Real continued Forward observation remains NOT_STARTED; all real sample counters remain zero, all production permissions false, UI/Focus routes unchanged and no V4-21 accepted head exists. R29 external acceptance and external closure of R28 P2 are carried from the supplied audit.\n\nFive evidence lanes and five capabilities remain independent with exact model/parameter/lineage partitions. Accepted-calendar session order and complete denominator ledgers preserve missed/non-evaluable sessions. Hidden eligible events remain in the cohort; no second original enrollment is accepted. Existing V4-15/16 owners retain all due, controls, benchmarks, settlement, price metrics and revision responsibilities. R30 does not implement a settlement engine or real writer.\n\nReadback preserves native outcome states alongside explicit observation states. Pending, missing, suspension, delisting and censoring never become arbitrary failures/successes; first-observed and corrected views retain immutable revisions with no double counting. Shadow/Production lane continuity requires exact compatible lineage and accepted migration/route bindings without relabeling old rows. Combined reports disclose lane/model/capability denominators and cannot satisfy gates through cross-lane borrowing.\n\nStrata and frozen windows are read-only and cannot change T0 eligibility, thresholds or model boundaries after outcomes. Gate readback pins owner receipts and never grants permission. Future recovery uses exact input digests, append-only superseding receipts and prior-head CAS.\n\nF21-01–F21-20 and 27 static checks operate on synthetic supplied ledgers only; no due-date, return or settlement calculations occur. Local and exact clean E-drive regression: 333 tests, 330 passed, the same three R26-A01 inherited failures, zero errors/skips/deselections. Original tracked and unrelated untracked bytes remain unchanged; LFS objects are exactly verified. Project temporary space uses E:.\n\nV4_21_CONTRACT_DESIGN = PASS_LOCAL_READY_FOR_EXTERNAL_AUDIT. V4_21_IMPLEMENTATION_ENTRY = BLOCKED_WAIT_REAL_OBSERVATION. NEXT = STOP_WAIT_R30_INDEPENDENT_EXTERNAL_AUDIT. Push is candidate publication, not external acceptance or a real observation grant.\n')
    files=[path for base in ('reports/r30','docs/evidence/r30') for path in (ROOT/base).rglob('*') if path.is_file() and path.suffix!='.pyc' and path.name!='R30_CONTRACT_CANDIDATE_SEAL.json']+[ROOT/'config/v4_21_continued_forward_observation_contract_v1.json',ROOT/'tests/test_v4_21_forward_observation_contract.py']
    write('reports/r30/R30_CONTRACT_CANDIDATE_SEAL.json',dict(baseline=BASE,tested_source_commit=source,tested_tag='codex/r30-forward-observation-contract-tested-source-20261004',files={path.relative_to(ROOT).as_posix():sha(path) for path in files},status='LOCAL_DESIGN_CANDIDATE_NOT_EXTERNAL_ACCEPTANCE',next_stage='STOP_WAIT_R30_INDEPENDENT_EXTERNAL_AUDIT'))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['local','clean','static','protected','seal']);parser.add_argument('--directory',default=str(ROOT));parser.add_argument('--source');a=parser.parse_args()
    if a.mode in ('local','clean'): regression(a.directory,a.mode)
    elif a.mode=='static': static_oracle()
    elif a.mode=='protected': protected()
    else: seal(a.source)
