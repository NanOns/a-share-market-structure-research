"""Static R29 design evaluation, E-only regression and additive candidate seal."""
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
from reports.r29.build_contract import BASE,sha,write
from reports.r29.design_resolver import vector_result


def protected():
    b=json.loads((ROOT/'reports/r29/PROTECTED_BASELINE.json').read_text(encoding='utf8'))
    changed=[n for n,d in b['tracked'].items() if not (ROOT/n).is_file() or sha(ROOT/n)!=d]
    unrelated=[n for n,d in b['unrelated'].items() if not (ROOT/n).is_file() or sha(ROOT/n)!=d]
    result=dict(baseline=BASE,tracked_count=len(b['tracked']),unrelated_count=len(b['unrelated']),changed=changed,unrelated_changed=unrelated,status='PASS' if not changed and not unrelated else 'FAIL',production_databases_opened=False,tdx_writes=False,actual_ui_router_changed=False,actual_focus_route_changed=False)
    write('reports/r29/PROTECTED_BYTES.json',result); assert result['status']=='PASS',result
    return result


def static_oracle():
    c=json.loads((ROOT/'config/v4_20_default_ui_cutover_contract_v1.json').read_text(encoding='utf8'))
    results={}
    for i,vector in enumerate(c['vectors'],1):
        actual=vector_result(i)
        assert not actual['actual_default_cutover'] and not actual['production_grant'] and actual['actual_route_changes']==[]
        results[vector['id']]=dict(actual=actual,status='PASS_DESIGN_SIMULATION_ONLY',independent_assertions='tests/test_v4_20_default_ui_contract.py::test_twenty_design_vectors')
    write('reports/r29/DESIGN_VECTOR_RESULTS.json',dict(scope='SYNTHETIC_DESIGN_NOT_REAL_UI_CUTOVER',results=results))
    case=results['U20-18']['actual']
    assert case['rollback_affected']==['ROTATION','SECTOR_RISK_CHANGE','SECTOR_STAGE','STOCK_SECTOR_DEPENDENT']
    assert all(case['modules'][m]['mode']=='LEGACY_PRODUCTION' for m in ('sector_research','rotation','sector_risk_change','stock_sector_dependent'))
    assert case['modules']['stock_research']['mode']=='PRODUCTION_V4'
    write('reports/r29/R28_P2_TRANSITIVE_ROLLBACK_CLOSURE.json',dict(item='R28_P2_ROLLBACK_TRANSITIVE_VECTOR_COVERAGE',scope='Sector Stage rollback cascades to Rotation/Sector Risk/Stock Sector Dependent while independent Stock Core remains valid',origin='docs/evidence/r29/V4_R28_V4_19_FOCUS_SOURCE_CUTOVER_CONTRACT_DESIGN_FINAL_INDEPENDENT_EXTERNAL_AUDIT_R1_20261004.md',evidence=['reports/r29/DESIGN_VECTOR_RESULTS.json#U20-18','tests/test_v4_20_default_ui_contract.py::test_r28_p2_transitive_rollback_independent_stock_preserved'],affected_capabilities=case['rollback_affected'],independent_stock_core='PRESERVED_PRODUCTION_V4_IN_SYNTHETIC_DESIGN',local_acceptance='COVERAGE_CLOSED_LOCAL_PENDING_R29_EXTERNAL_AUDIT',runtime_acceptance='NOT_GRANTED',r28_frozen_contract_reopened=False))


def regression(directory,label):
    from reports.r26.run_regression import scope
    directory=Path(directory).resolve(); assert directory.drive.upper() in ('E:','F:')
    temp=Path('E:/codex_tmp/test_temp')/('r29-'+label)
    env=dict(os.environ,TEMP=str(temp.parent),TMP=str(temp.parent),TMPDIR=str(temp.parent),PYTHONDONTWRITEBYTECODE='1',PYTHONPATH='src'+os.pathsep+'.',PYTHONIOENCODING='utf-8',WORKBENCH_API_BACKEND='duckdb',WORKBENCH_PG_DSN='dbname=r29_mock host=127.0.0.1 port=1 connect_timeout=1')
    names=scope()+['tests/test_v4_17_shadow_ui.py','tests/test_v4_18_migration_contract.py','tests/test_v4_19_focus_cutover_contract.py','tests/test_v4_20_default_ui_contract.py']
    capture=temp.parent/('r29-'+label+'.xml')
    result=subprocess.run([sys.executable,'-m','pytest',*names,'-q','--basetemp='+str(temp),'--junitxml='+str(capture)],cwd=directory,env=env,capture_output=True)
    raw=capture.read_bytes(); prefix='reports/r29/'+label
    write(prefix+'-tests.xml',raw.decode('utf8')); write(prefix+'-output.txt',(result.stdout+result.stderr).decode('utf8'))
    tree=ET.fromstring(raw); cases=tree.findall('.//testcase'); failures=[t.get('classname')+'::'+t.get('name') for t in cases if t.find('failure') is not None]
    debt={'tests.upgrade_v3.test_v3_unified_entry::test_v3_is_the_single_unified_workbench_entry','tests.upgrade_v3.test_p01_01_lock_scope::test_hot_rank_route_skips_request_scope','tests.upgrade_v3.test_p01_01_lock_scope::test_send_marks_disconnected_client_closed'}
    errors=len(tree.findall('.//error')); skipped=len(tree.findall('.//skipped'))
    s=dict(directory=str(directory),source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=directory,text=True).strip(),scope=names,tests=len(cases),passed=len(cases)-len(failures)-errors-skipped,failures=failures,errors=errors,skipped=skipped,deselected=0,exit_code=result.returncode,temporary_directory=str(temp),captured_xml_sha256=hashlib.sha256(raw).hexdigest(),captured_output_sha256=hashlib.sha256(result.stdout+result.stderr).hexdigest(),status='PASS_SCOPED_NO_NEW_FAILURES' if set(failures)==debt and errors==skipped==0 else 'FAIL',historical_debt='R26_A01_OPEN_NONBLOCKING_EXTERNAL_R26_R27_R28; NO_TEST_WEAKENING_OR_DESELECTION')
    write(prefix+'-summary.json',s); print(json.dumps({k:v for k,v in s.items() if k!='scope'},ensure_ascii=False),flush=True); assert s['status']=='PASS_SCOPED_NO_NEW_FAILURES',s


def seal(source):
    p=protected(); static_oracle()
    c=json.loads((ROOT/'config/v4_20_default_ui_cutover_contract_v1.json').read_text(encoding='utf8')); bindings={}
    for path in sorted((ROOT/'reports/r29').glob('*.json')):
        value=json.loads(path.read_text(encoding='utf8'))
        if 'section' in value:
            assert value['definition']==c[value['section']] and value['contract_sha256']==sha(ROOT/'config/v4_20_default_ui_cutover_contract_v1.json')
            bindings[path.name]='EXACT_SECTION_AND_SHA256'
    assert len(bindings)==9
    local=json.loads((ROOT/'reports/r29/local-summary.json').read_text(encoding='utf8')); clean=json.loads((ROOT/'reports/r29/clean-summary.json').read_text(encoding='utf8'))
    assert clean['source_commit']==source and clean['tests']==local['tests']==306
    write('reports/r29/LOCAL_TEST_SUMMARY.json',local); write('reports/r29/CLEAN_REGRESSION.json',clean)
    write('reports/r29/DEFAULT_UI_CONTRACT_GATE.json',dict(status='PASS_LOCAL_READY_FOR_EXTERNAL_AUDIT',scope='DEFAULT_UI_CUTOVER_CONTRACT_DESIGN_ONLY',bindings=bindings,product_modules=6,total_modules_and_subcomponents=9,design_vectors=20,protected=p['status'],implementation_entry='BLOCKED_WAIT_PRODUCTION_PERMISSION',DEFAULT_UI_CUTOVER=False,V4_20_ACCEPTED_HEAD='NOT_CREATED',R28_P2='COVERAGE_CLOSED_LOCAL_PENDING_EXTERNAL_AUDIT',next_stage=c['next_stage']))
    write('reports/r29/AUDIT_ITEM_CARRY.json',dict(item='R26_A01_INHERITED_V3_REGRESSION',scope='V3 unified-entry source literal and two _NoopService status mocks',evidence=['reports/r29/clean-tests.xml','docs/evidence/r29/V4_R28_V4_19_FOCUS_SOURCE_CUTOVER_CONTRACT_DESIGN_FINAL_INDEPENDENT_EXTERNAL_AUDIT_R1_20261004.md'],acceptance='OPEN_NONBLOCKING_HISTORICAL_DEBT; SEPARATE_REPAIR_AND_ACCEPTANCE_REQUIRED',r29='NO_AUTOMATIC_CLOSURE'))
    write('docs/evidence/r29/R29_CONTRACT_DESIGN_ACCEPTANCE.md','# R29 V4-20 Default UI Cutover contract design\n\nBaseline: `'+BASE+'`. Exact tested source: `'+source+'`.\n\nR29 freezes future UI semantics only. Current defaults remain Legacy production plus the explicit Shadow engineering page. Production permissions are all false; no router, default UI, Focus route, accepted head or runtime authority changed.\n\nThe six product modules and three dependent subcomponents have exact capability mappings. Composite containers never gain V4 through an empty dependency list. Required active accepted permissions resolve only an exact bound V4 publication; otherwise an exact Legacy route remains. Explicit Shadow is read-only and never a production fallback. Missing or mismatched exact bindings fail closed with UNKNOWN.\n\nMixed pages retain native sub-context namespaces and explicit mode/PROVISIONAL labels. Deep links pin old accepted contexts and remain historical read-only after cutover. Route/permission changes invalidate affected live caches and sessions rather than silently merging or rebasing. Focus writes require current V4-19 route, capability permission and exact endpoint identity/head agreement; Legacy authority and user product state are retained.\n\nU20-01–U20-20 are synthetic design vectors, not UI runtime acceptance. U20-18 independently demonstrates Sector rollback affecting Rotation, Sector Risk Change and Stock Sector Dependent while Stock Core remains valid. R28 P2 coverage is closed locally, pending R29 external review; the frozen R28 contract remains unchanged.\n\nLocal and exact clean E-drive regression: 306 tests, 303 passed, the same three R26-A01 inherited failures, zero errors/skips/deselections. All existing tracked bytes and unrelated untracked files remain unchanged. Exact LFS objects are verified in the clean checkout. Project temporary checkouts, captures and caches use E:.\n\nV4_20_CONTRACT_DESIGN = PASS_LOCAL_READY_FOR_EXTERNAL_AUDIT. V4_20_IMPLEMENTATION_ENTRY = BLOCKED_WAIT_PRODUCTION_PERMISSION. NEXT = STOP_WAIT_R29_INDEPENDENT_EXTERNAL_AUDIT. Push publishes a reviewable candidate and grants no external acceptance.\n')
    files=[path for base in ('reports/r29','docs/evidence/r29') for path in (ROOT/base).rglob('*') if path.is_file() and path.suffix!='.pyc' and path.name!='R29_CONTRACT_CANDIDATE_SEAL.json']+[ROOT/'config/v4_20_default_ui_cutover_contract_v1.json',ROOT/'tests/test_v4_20_default_ui_contract.py']
    write('reports/r29/R29_CONTRACT_CANDIDATE_SEAL.json',dict(baseline=BASE,tested_source_commit=source,tested_tag='codex/r29-default-ui-contract-tested-source-20261004',files={path.relative_to(ROOT).as_posix():sha(path) for path in files},status='LOCAL_DESIGN_CANDIDATE_NOT_EXTERNAL_ACCEPTANCE',next_stage='STOP_WAIT_R29_INDEPENDENT_EXTERNAL_AUDIT'))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['local','clean','static','protected','seal']);parser.add_argument('--directory',default=str(ROOT));parser.add_argument('--source');a=parser.parse_args()
    if a.mode in ('local','clean'): regression(a.directory,a.mode)
    elif a.mode=='static': static_oracle()
    elif a.mode=='protected': protected()
    else: seal(a.source)
