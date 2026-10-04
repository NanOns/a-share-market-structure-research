"""R28 read-only oracle, scoped regression, protected bytes and candidate seal."""
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
from reports.r28.build_contract import BASE,sha,write
from reports.r28.design_oracle import vector_result


def protected():
    b=json.loads((ROOT/'reports/r28/PROTECTED_BASELINE.json').read_text(encoding='utf8'))
    changed=[n for n,d in b['tracked'].items() if not (ROOT/n).is_file() or sha(ROOT/n)!=d]
    unrelated=[n for n,d in b['unrelated'].items() if not (ROOT/n).is_file() or sha(ROOT/n)!=d]
    result=dict(baseline=BASE,tracked_count=len(b['tracked']),unrelated_count=len(b['unrelated']),changed=changed,unrelated_changed=unrelated,status='PASS' if not changed and not unrelated else 'FAIL',production_databases_opened=False,tdx_writes=False,production_routing_writer_implemented=False)
    write('reports/r28/PROTECTED_BYTES.json',result)
    assert result['status']=='PASS',result
    return result


def static_oracle():
    c=json.loads((ROOT/'config/v4_19_focus_source_cutover_contract_v1.json').read_text(encoding='utf8'))
    results={}
    for vector in c['vectors']:
        actual=vector_result(vector['id']); expected=vector['expected']
        assert actual['design_action']==expected['design_action']
        assert actual['reason']==expected['reason']
        assert actual['hypothetical_permissions']['STOCK_CORE']==expected['stock_core_permission']
        assert actual['production_grant'] is False and actual['route_changes']==[]
        results[vector['id']]=dict(actual=actual,expected=expected,status='PASS_DESIGN_SIMULATION_ONLY')
    write('reports/r28/DESIGN_VECTOR_RESULTS.json',dict(scope='SYNTHETIC_DESIGN_NOT_REAL_ACCEPTANCE',results=results))
    write('reports/r28/DEPENDENCY_MATRIX.json',dict(contract_dependency_graph=c['permission_formula']['dependency_graph'],examples={v:results[v]['actual'] for v in ('C02','C03','C04','C11','C15','C20')},current_permissions=c['current_state']['production_permission'],scope='HYPOTHETICAL_EXAMPLES_NEVER_ACTUAL_GRANTS'))


def regression(directory,label):
    from reports.r26.run_regression import scope
    directory=Path(directory).resolve(); assert directory.drive.upper() in ('E:','F:')
    temp=Path('E:/codex_tmp/test_temp')/('r28-'+label)
    env=dict(os.environ,TEMP=str(temp.parent),TMP=str(temp.parent),TMPDIR=str(temp.parent),PYTHONDONTWRITEBYTECODE='1',PYTHONPATH='src'+os.pathsep+'.',PYTHONIOENCODING='utf-8',WORKBENCH_API_BACKEND='duckdb',WORKBENCH_PG_DSN='dbname=r28_mock host=127.0.0.1 port=1 connect_timeout=1')
    names=scope()+['tests/test_v4_17_shadow_ui.py','tests/test_v4_18_migration_contract.py','tests/test_v4_19_focus_cutover_contract.py']
    capture=temp.parent/('r28-'+label+'.xml')
    result=subprocess.run([sys.executable,'-m','pytest',*names,'-q','--basetemp='+str(temp),'--junitxml='+str(capture)],cwd=directory,env=env,capture_output=True)
    raw=capture.read_bytes(); prefix='reports/r28/'+label
    write(prefix+'-tests.xml',raw.decode('utf8')); write(prefix+'-output.txt',(result.stdout+result.stderr).decode('utf8'))
    tree=ET.fromstring(raw); cases=tree.findall('.//testcase'); failures=[t.get('classname')+'::'+t.get('name') for t in cases if t.find('failure') is not None]
    debt={'tests.upgrade_v3.test_v3_unified_entry::test_v3_is_the_single_unified_workbench_entry','tests.upgrade_v3.test_p01_01_lock_scope::test_hot_rank_route_skips_request_scope','tests.upgrade_v3.test_p01_01_lock_scope::test_send_marks_disconnected_client_closed'}
    errors=len(tree.findall('.//error')); skipped=len(tree.findall('.//skipped'))
    s=dict(directory=str(directory),source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=directory,text=True).strip(),scope=names,tests=len(cases),passed=len(cases)-len(failures)-errors-skipped,failures=failures,errors=errors,skipped=skipped,deselected=0,exit_code=result.returncode,temporary_directory=str(temp),captured_xml_sha256=hashlib.sha256(raw).hexdigest(),captured_output_sha256=hashlib.sha256(result.stdout+result.stderr).hexdigest(),status='PASS_SCOPED_NO_NEW_FAILURES' if set(failures)==debt and errors==skipped==0 else 'FAIL',historical_debt='R26_A01_OPEN_NONBLOCKING_EXTERNAL_R26_R27; NO_TEST_WEAKENING_OR_DESELECTION')
    write(prefix+'-summary.json',s); print(json.dumps({k:v for k,v in s.items() if k!='scope'},ensure_ascii=False),flush=True)
    assert s['status']=='PASS_SCOPED_NO_NEW_FAILURES',s


def seal(source):
    p=protected(); static_oracle()
    c=json.loads((ROOT/'config/v4_19_focus_source_cutover_contract_v1.json').read_text(encoding='utf8'))
    bindings={}
    for path in sorted((ROOT/'reports/r28').glob('*.json')):
        value=json.loads(path.read_text(encoding='utf8'))
        if 'section' in value:
            assert value['definition']==c[value['section']] and value['contract_sha256']==sha(ROOT/'config/v4_19_focus_source_cutover_contract_v1.json')
            bindings[path.name]='EXACT_SECTION_AND_SHA256'
    assert len(bindings)==8
    local=json.loads((ROOT/'reports/r28/local-summary.json').read_text(encoding='utf8'))
    clean=json.loads((ROOT/'reports/r28/clean-summary.json').read_text(encoding='utf8'))
    assert clean['source_commit']==source and clean['tests']==local['tests']==280
    write('reports/r28/LOCAL_TEST_SUMMARY.json',local); write('reports/r28/CLEAN_REGRESSION.json',clean)
    write('reports/r28/CUTOVER_CONTRACT_GATE.json',dict(status='PASS_LOCAL_READY_FOR_EXTERNAL_AUDIT',scope='CUTOVER_V2_CONTRACT_DESIGN_ONLY',bindings=bindings,capabilities=5,design_vectors=20,protected=p['status'],implementation_entry='BLOCKED_WAIT_REAL_GATES',production_permission=c['current_state']['production_permission'],focus_source_cutover=False,V4_19_ACCEPTED_HEAD='NOT_CREATED',next_stage=c['next_stage']))
    write('reports/r28/AUDIT_ITEM_CARRY.json',dict(item='R26_A01_INHERITED_V3_REGRESSION',scope='V3 unified-entry source literal and two _NoopService status mocks',evidence=['reports/r28/clean-tests.xml','docs/evidence/r28/V4_R27_V4_18_MIGRATION_REPLAY_CONTRACT_DESIGN_FINAL_INDEPENDENT_EXTERNAL_AUDIT_R1_20261004.md'],acceptance='OPEN_NONBLOCKING_HISTORICAL_DEBT; SEPARATE_REPAIR_AND_ACCEPTANCE_REQUIRED',r28='NO_AUTOMATIC_CLOSURE'))
    write('docs/evidence/r28/R28_CONTRACT_DESIGN_ACCEPTANCE.md','# R28 V4-19 Focus Source Cutover contract design\n\nBaseline: `'+BASE+'`. Exact tested source: `'+source+'`.\n\nCUTOVER_V2 is frozen per capability: Shadow stable AND Forward AND externally accepted runtime Migration Replay AND all dependency permissions. R27 design acceptance does not satisfy migration runtime. Current production permissions are all false; no Focus route, accepted head or business authority changed.\n\nThe five capabilities have explicit dependency, fallback, UI, Focus and rollback policies. Stock requires 20 consecutive accepted market sessions, zero temporal/P0/identity corruption and a rollback drill, followed by at least five distinct signal dates and thirty distinct stocks with positive-event T5 OBSERVED outcomes. Controls/benchmarks require quality receipts. Sector/Rotation require separately frozen policies and never borrow stock counts.\n\nThe receipt schema pins exact identities, dependency scope and active gate receipts. Future cutover is atomic with route and dependency-head CAS. Mixed UI binds exact module publications into a shared immutable context manifest while retaining each module namespace/mode. Capability rollback preserves facts, user work and settlement ownership; affected dependent consumers fail closed and independent capabilities remain valid.\n\nC01–C20 run only against synthetic design fixtures. Hypothetical permissions are never emitted as actual production grants or route changes. Static tests independently verify design expectations, thresholds, identity conflicts, quality degradation, deduplication and rollback scope.\n\nLocal and clean E-drive regression: 280 tests, 277 passed, the same three R26-A01 inherited failures, zero errors/skips/deselections. Existing tracked bytes and 109 unrelated untracked files are unchanged. LFS objects are independently hashed in the exact clean checkout. All project temporary space is on E:.\n\nV4_19_CONTRACT_DESIGN = PASS_LOCAL_READY_FOR_EXTERNAL_AUDIT. V4_19_IMPLEMENTATION_ENTRY = BLOCKED_WAIT_REAL_GATES. NEXT = STOP_WAIT_R28_INDEPENDENT_EXTERNAL_AUDIT. Push is candidate publication, not external acceptance.\n')
    files=[path for base in ('reports/r28','docs/evidence/r28') for path in (ROOT/base).rglob('*') if path.is_file() and path.suffix!='.pyc' and path.name!='R28_CONTRACT_CANDIDATE_SEAL.json']+[ROOT/'config/v4_19_focus_source_cutover_contract_v1.json',ROOT/'tests/test_v4_19_focus_cutover_contract.py']
    write('reports/r28/R28_CONTRACT_CANDIDATE_SEAL.json',dict(baseline=BASE,tested_source_commit=source,tested_tag='codex/r28-focus-cutover-contract-tested-source-20261004',files={path.relative_to(ROOT).as_posix():sha(path) for path in files},status='LOCAL_DESIGN_CANDIDATE_NOT_EXTERNAL_ACCEPTANCE',next_stage='STOP_WAIT_R28_INDEPENDENT_EXTERNAL_AUDIT'))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['local','clean','static','protected','seal']);parser.add_argument('--directory',default=str(ROOT));parser.add_argument('--source');a=parser.parse_args()
    if a.mode in ('local','clean'): regression(a.directory,a.mode)
    elif a.mode=='static': static_oracle()
    elif a.mode=='protected': protected()
    else: seal(a.source)
