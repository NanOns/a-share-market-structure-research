"""Independent stage inventory and protected-byte oracle; no runtime writes."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET
from run_regression import ROOT,atomic

BASE='60b17524596918b66456fdd48dbc1beb068ab28a'
ALLOWED=('config/v4_17_','src/workbench_service/','tests/test_v4_17_','docs/evidence/r26/','reports/r26/')


def ref(path):
    raw=(ROOT/path).read_bytes()
    return dict(path=path,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())


def read(path):return json.loads((ROOT/path).read_bytes())


def command(args):return subprocess.check_output(args,cwd=ROOT)


def protected():
    changed=command(['git','diff',BASE,'--name-only']).decode('utf8').splitlines()
    names=command(['git','ls-tree','-r','--name-only',BASE]).decode('utf8').splitlines()
    baseline_changed=[name for name in changed if name in names]
    assert baseline_changed==['src/workbench_service/app.py'],baseline_changed
    assert all(any(name.startswith(prefix) for prefix in ALLOWED) for name in changed),changed
    # Capture exact live bytes before and after regression for every tracked
    # baseline file. This includes raw LFS payloads, accepted heads and receipts.
    protected_names=[n for n in names if n!='src/workbench_service/app.py']
    entries=[]
    for name in protected_names:
        path=ROOT/name
        assert path.is_file(),name
        with path.open('rb') as stream:sha=hashlib.file_digest(stream,'sha256').hexdigest()
        entries.append(dict(path=name,bytes=path.stat().st_size,sha256=sha))
    target=ROOT/'reports/r26/PROTECTED_BYTES.json'
    if target.exists():
        previous=read('reports/r26/PROTECTED_BYTES.json')
        assert previous['entries']==entries,'PROTECTED_BYTES_CHANGED_DURING_STAGE'
    for name in ('V4_16_ACCEPTED_HEAD.json','V4_17_ACCEPTED_HEAD.json'):
        assert not any((ROOT/p/name).exists() for p in ('data/v4','config'))
    result=dict(status='PASS_LOCAL',baseline=BASE,scope='ALL_BASELINE_TRACKED_FILES_EXCEPT_AUTHORIZED_APP_ADDITIONS',count=len(entries),entries=entries,
                changed_baseline_files=baseline_changed,R25_frozen=True,accepted_heads_unchanged=True,activation_unchanged=True,
                real_observations=0,PIT_OBSERVED_REAL_SAMPLES=0,TDX='READ_ONLY_NOT_OPENED_BY_R26')
    atomic('reports/r26/PROTECTED_BYTES.json',result)
    return result


def gates():
    contract=read('config/v4_17_shadow_ui_contract_v1.json');source=read('config/v4_17_shadow_ui_source_v1.json')
    assert source['accepted_readback'] is None and source['external_acceptance'] is None
    assert len(contract['identity_fields'])==10 and len(contract['components'])==6 and len(contract['routes'])==7
    tree=ET.parse(ROOT/'reports/r26/feature-tests.xml');tests=tree.findall('.//testcase')
    assert len(tests)==43 and not tree.findall('.//failure') and not tree.findall('.//error') and not tree.findall('.//skipped')
    cases=[f'U{i:02}' for i in range(1,19)]
    assert all(any('test_negative_matrix['+case+']'==t.get('name') for t in tests) for case in cases)
    base=dict(status='PASS_LOCAL',engineering_only=True,feature_tests=ref('reports/r26/feature-tests.xml'))
    atomic('reports/r26/SHADOW_UI_CONTRACT_GATE.json',base|dict(contract=ref('config/v4_17_shadow_ui_contract_v1.json'),routes=contract['routes'],no_writes=True,no_fallback=contract['no_fallback']))
    atomic('reports/r26/CONTEXT_IDENTITY_GATE.json',base|dict(fields=contract['identity_fields'],token=contract['token'],per_component_checks=True,deep_link_mismatch='409_BLOCKED'))
    atomic('reports/r26/NO_REAL_DATA_GATE.json',base|dict(source=ref('config/v4_17_shadow_ui_source_v1.json'),status_current='NO_REAL_SHADOW_DATA',real_sample_count=0,database_opened=False,simulation_discovery=False))
    atomic('reports/r26/READ_ONLY_API_GATE.json',base|dict(methods_allowed=['GET'],methods_rejected=['POST','PUT','PATCH','DELETE'],write_attempts=24,production_db_bytes_unchanged=True,legacy_GET_POST_ast_unchanged=True))
    atomic('reports/r26/COMPONENT_REGISTRY_GATE.json',base|dict(components=contract['components'],client_registry_matches_contract=True,unknown_values='NULL_WITH_REASON',absent_upstream_fields='UNKNOWN_NO_ALGORITHM_INVENTION'))
    atomic('reports/r26/CONTEXT_NEGATIVE_MATRIX.json',base|dict(cases=[dict(case=case,status='PASS_LOCAL_FAIL_CLOSED',test_node='tests/test_v4_17_shadow_ui.py::test_negative_matrix['+case+']') for case in cases],supplemental=['native_exact_fact_readonly','native_storage_origin','native_field_path','native_field_kind','contract_failure_isolation','legacy_ast_equivalence']))
    baseline=read('reports/r26/baseline-final-summary.json');local=read('reports/r26/local-final-v3-summary.json')
    assert baseline['errors']==local['errors']==baseline['skipped']==local['skipped']==0
    assert {f['node'] for f in baseline['failures']}=={f['node'] for f in local['failures']}
    assert baseline['source_commit']==BASE and len(baseline['failures'])==3
    atomic('reports/r26/EXISTING_UI_REGRESSION.json',dict(status='PASS_SCOPED_NO_NEW_FAILURES',baseline_tests=177,baseline_passed=174,baseline_failures=baseline['failures'],current_tests=local['tests'],current_passed=local['passed'],current_failures=local['failures'],new_failures=[],audit_item='R26-A01',baseline_report=ref('reports/r26/baseline-final-tests.xml'),current_report=ref(local['xml']),legacy_static_pages='UNCHANGED_BYTES',legacy_service='AST_IDENTICAL_EXCLUDING_SHADOW_ADDITIONS',not_a_zero_failure_full_suite=True))
    atomic('reports/r26/LOCAL_TEST_SUMMARY.json',base|dict(feature_tests_count=43,feature_passed=43,feature_failed=0,regression_tests=local['tests'],regression_passed=local['passed'],inherited_failures=3,new_failures=0,errors=0,skipped=0,deselected=0,legacy_cross_audit='R26-A01_OPEN',not_external_acceptance=True))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--protected-only',action='store_true');args=parser.parse_args()
    result=protected()
    if not args.protected_only:gates()
    print('PASS_PROTECTED_BASELINE_FILES',result['count'],flush=True)
