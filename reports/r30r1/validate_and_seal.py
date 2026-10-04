"""Read-only native owner repair checks, complete regression and additive seal."""
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
from reports.r30r1.build_repair import ALLOWED,BASE,CONTRACT,PASS_KEEP,baseline_contract,sha,write


def protected():
    b=json.loads((ROOT/'reports/r30r1/PROTECTED_BASELINE.json').read_text(encoding='utf8'))
    changed=[n for n,d in b['tracked'].items() if n not in ALLOWED and (not (ROOT/n).is_file() or sha(ROOT/n)!=d)]
    unrelated=[n for n,d in b['unrelated'].items() if not (ROOT/n).is_file() or sha(ROOT/n)!=d]
    c=json.loads((ROOT/CONTRACT).read_bytes()); old=baseline_contract()
    sections={key:dict(before_sha256=hashlib.sha256(json.dumps(old[key],sort_keys=True).encode()).hexdigest(),after_sha256=hashlib.sha256(json.dumps(c[key],sort_keys=True).encode()).hexdigest(),unchanged=c[key]==old[key]) for key in PASS_KEEP}
    assert all(v['unchanged'] for v in sections.values())
    assert c['owner_bindings'][:-1]==old['owner_bindings']
    for key in old['receipt_schema']:
        if key=='additional': assert c['receipt_schema'][key][:len(old['receipt_schema'][key])]==old['receipt_schema'][key]
        else: assert c['receipt_schema'][key]==old['receipt_schema'][key]
    assert all(c['vectors'][i]==old['vectors'][i] for i in range(20) if i not in (0,4,5))
    result=dict(baseline=BASE,tracked_count=len(b['tracked']),allowed_changed_files=list(ALLOWED),unexpected_changed=changed,unrelated_count=len(b['unrelated']),unrelated_changed=unrelated,PASS_KEEP_sections=sections,status='PASS' if not changed and not unrelated else 'FAIL',production_databases_opened=False,actual_real_rows_written=0,tdx_writes=False,settlement_owner_changed=False,Focus_default_UI_route_changed=False)
    write('reports/r30r1/PROTECTED_BYTES.json',result); assert result['status']=='PASS',result
    return result


def static_checks():
    from reports.r30.design_ledger import vector_result,readback,fixture,scenario
    from reports.r30r1.session_authority import receipt_session_status,OWNER,OWNER_SHA
    from tests.test_v4_21_native_session_repair import negative
    c=json.loads((ROOT/CONTRACT).read_bytes()); binding=c['native_session_policy']['shadow_owner']
    assert binding['sha256']==OWNER_SHA and binding['native_slot_states']==OWNER['slot_states']
    f={}
    for i in range(1,21):
        result=vector_result(i); assert result['status']==c['vectors'][i-1]['expected_status'] and result['actual_real_rows_written']==0
        f[f'F21-{i:02}']=dict(result=result,scope='DESIGN_ONLY')
    write('reports/r30r1/F21_REGRESSION.json',dict(results=f,status='PASS_LOCAL_DESIGN_ONLY',production_future_authority='EXPLICIT_SIMULATION_ONLY_NOT_CURRENT_BINDING'))
    matrix={}
    for i in range(1,9):
        result=readback(negative(i)); assert result['status']=='BLOCKED_AFFECTED_SCOPE'
        matrix[f'S21-{i:02}']=dict(result=result,expected='BLOCKED_AFFECTED_SCOPE',scope='SYNTHETIC_NEGATIVE_NOT_REAL_EVIDENCE')
    write('reports/r30r1/NATIVE_STATUS_NEGATIVE_MATRIX.json',dict(status='PASS_LOCAL',vectors=matrix))
    write('reports/r30r1/RECEIPT_STATUS_EXAMPLES.json',dict(scope='DESIGN_ONLY_NO_REAL_RECEIPT',examples={f'F21-{i:02}':receipt_session_status(scenario(i)['sessions'][-1]) for i in (1,5,6)}))


def regression(directory,label):
    from reports.r26.run_regression import scope
    directory=Path(directory).resolve(); assert directory.drive.upper() in ('E:','F:')
    temp=Path('E:/codex_tmp/test_temp')/('r30r1-'+label)
    env=dict(os.environ,TEMP=str(temp.parent),TMP=str(temp.parent),TMPDIR=str(temp.parent),PYTHONDONTWRITEBYTECODE='1',PYTHONPATH='src'+os.pathsep+'.',PYTHONIOENCODING='utf-8',WORKBENCH_API_BACKEND='duckdb',WORKBENCH_PG_DSN='dbname=r30r1_mock host=127.0.0.1 port=1 connect_timeout=1')
    names=scope()+['tests/test_v4_17_shadow_ui.py','tests/test_v4_18_migration_contract.py','tests/test_v4_19_focus_cutover_contract.py','tests/test_v4_20_default_ui_contract.py','tests/test_v4_21_forward_observation_contract.py','tests/test_v4_21_native_session_repair.py']
    capture=temp.parent/('r30r1-'+label+'.xml')
    result=subprocess.run([sys.executable,'-m','pytest',*names,'-q','--basetemp='+str(temp),'--junitxml='+str(capture)],cwd=directory,env=env,capture_output=True)
    raw=capture.read_bytes(); prefix='reports/r30r1/'+label
    write(prefix+'-tests.xml',raw.decode('utf8')); write(prefix+'-output.txt',(result.stdout+result.stderr).decode('utf8'))
    tree=ET.fromstring(raw); cases=tree.findall('.//testcase'); failures=[t.get('classname')+'::'+t.get('name') for t in cases if t.find('failure') is not None]
    debt={'tests.upgrade_v3.test_v3_unified_entry::test_v3_is_the_single_unified_workbench_entry','tests.upgrade_v3.test_p01_01_lock_scope::test_hot_rank_route_skips_request_scope','tests.upgrade_v3.test_p01_01_lock_scope::test_send_marks_disconnected_client_closed'}
    errors=len(tree.findall('.//error')); skipped=len(tree.findall('.//skipped'))
    s=dict(directory=str(directory),source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=directory,text=True).strip(),scope=names,tests=len(cases),passed=len(cases)-len(failures)-errors-skipped,failures=failures,errors=errors,skipped=skipped,deselected=0,exit_code=result.returncode,temporary_directory=str(temp),captured_xml_sha256=hashlib.sha256(raw).hexdigest(),captured_output_sha256=hashlib.sha256(result.stdout+result.stderr).hexdigest(),status='PASS_SCOPED_NO_NEW_FAILURES' if set(failures)==debt and errors==skipped==0 else 'FAIL',historical_debt='R26_A01_OPEN_NONBLOCKING_EXTERNAL; NO_DESELECTION')
    write(prefix+'-summary.json',s); print(json.dumps({k:v for k,v in s.items() if k!='scope'},ensure_ascii=False),flush=True); assert s['status']=='PASS_SCOPED_NO_NEW_FAILURES',s


def seal(source):
    p=protected(); static_checks()
    c=json.loads((ROOT/CONTRACT).read_bytes())
    local=json.loads((ROOT/'reports/r30r1/local-summary.json').read_bytes()); clean=json.loads((ROOT/'reports/r30r1/clean-summary.json').read_bytes())
    assert clean['source_commit']==source and clean['tests']==local['tests']==346
    write('reports/r30r1/LOCAL_TEST_SUMMARY.json',local); write('reports/r30r1/CLEAN_REGRESSION.json',clean)
    write('reports/r30r1/NATIVE_SESSION_REPAIR_GATE.json',dict(R30R1_NATIVE_SESSION_STATUS_BINDING='PASS_LOCAL_READY_FOR_EXTERNAL_AUDIT',V4_21_CONTRACT_DESIGN='PASS_LOCAL_READY_FOR_EXTERNAL_AUDIT',V4_21_IMPLEMENTATION_ENTRY='BLOCKED_WAIT_REAL_OBSERVATION',REAL_CONTINUED_FORWARD_OBSERVATION='NOT_STARTED',V4_21_ACCEPTED_HEAD='NOT_CREATED',protected=p['status'],next='STOP_WAIT_R30R1_INDEPENDENT_EXTERNAL_AUDIT'))
    write('reports/r30r1/AUDIT_ITEM_DISPOSITION.json',dict(native_status_P0='REPAIRED_LOCAL_PENDING_EXTERNAL_ACCEPTANCE',shadow_owner_P0='EXACT_OWNER_ID_SHA_AND_NATIVE_STATES_BOUND_LOCAL',production_authority_P1='FUTURE_ACCEPTED_BINDING_REQUIRED_CURRENTLY_NOT_COUNTABLE',R26_A01='OPEN_NONBLOCKING_HISTORICAL_DEBT_SEPARATE',evidence=['reports/r30r1/NATIVE_STATUS_NEGATIVE_MATRIX.json','reports/r30r1/PROTECTED_BYTES.json','reports/r30r1/CLEAN_REGRESSION.json']))
    write('docs/evidence/r30r1/R30R1_REPAIR_ACCEPTANCE.md','# R30R1 Native session status and owner binding repair\n\nBaseline: `'+BASE+'`. Exact tested source: `'+source+'`.\n\nR30 used generic session statuses and omitted the accepted native slot owner. This repair binds the exact V4-16 Observation Slot V2 ID, file digest and native states. Shadow ACCEPTED_ON_TIME and MISSED_OBSERVATION_SLOT are distinct from projection_evaluable and its reason. Accepted-but-non-evaluable is retained as accepted native status, counts zero and resets streak without becoming missed. Alias/unknown states, wrong/missing owner binding, inconsistent count claims and missed-but-evaluable rows are rejected.\n\nObservation receipt status is exact native status with separate projection fields. Production native authority remains FUTURE_ACCEPTED_BINDING_REQUIRED and real-gate evidence NOT_COUNTABLE. Future Production examples exist only in explicitly marked CONTRACT_DESIGN_SIMULATION fixtures with simulated binding; they grant no current authority.\n\nF21-01/05/06 are normalized; remaining F21 semantics and all PASS_KEEP contract sections remain unchanged. Historical R30 reports/seal retain their original bytes and audit meaning; they are not rewritten to conceal the repair. No real writer, settlement engine, gate grant, Focus/UI route change or accepted head is created.\n\nLocal and clean regression: 346 tests, 343 passed, only the same three inherited R26-A01 failures, no errors/skips/deselections. Eight S21 negative cases and independent native-contract assertions pass. All other existing tracked files and unrelated work remain unchanged. Clean checkout/LFS proof uses F:/codex_tmp; tests/captures use E:/codex_tmp/test_temp.\n\nLocal repair is ready for independent external audit; implementation remains BLOCKED_WAIT_REAL_OBSERVATION and real continued Forward observation NOT_STARTED. NEXT = STOP_WAIT_R30R1_INDEPENDENT_EXTERNAL_AUDIT. Push does not close the external P0 findings by itself.\n')
    files=[path for base in ('reports/r30r1','docs/evidence/r30r1') for path in (ROOT/base).rglob('*') if path.is_file() and path.suffix!='.pyc' and path.name!='R30R1_CANDIDATE_SEAL.json']+[ROOT/path for path in ALLOWED]+[ROOT/'tests/test_v4_21_native_session_repair.py']
    write('reports/r30r1/R30R1_CANDIDATE_SEAL.json',dict(baseline=BASE,tested_source_commit=source,tested_tag='codex/r30r1-native-session-repair-tested-source-20261004',files={path.relative_to(ROOT).as_posix():sha(path) for path in files},status='LOCAL_REPAIR_CANDIDATE_NOT_EXTERNAL_ACCEPTANCE',next_stage='STOP_WAIT_R30R1_INDEPENDENT_EXTERNAL_AUDIT'))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['local','clean','static','protected','seal']);parser.add_argument('--directory',default=str(ROOT));parser.add_argument('--source');a=parser.parse_args()
    if a.mode in ('local','clean'): regression(a.directory,a.mode)
    elif a.mode=='static': static_checks()
    elif a.mode=='protected': protected()
    else: seal(a.source)
