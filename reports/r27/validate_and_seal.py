"""Read-only static oracle and E-drive regression evidence, not migration execution."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from reports.r27.build_contract import BASE, sha, write


def check_protected():
    baseline = json.loads((ROOT/'reports/r27/PROTECTED_BASELINE.json').read_text(encoding='utf8'))
    changed = [name for name,digest in baseline['tracked'].items() if not (ROOT/name).is_file() or sha(ROOT/name) != digest]
    unrelated = [name for name,digest in baseline['unrelated'].items() if not (ROOT/name).is_file() or sha(ROOT/name) != digest]
    result = dict(baseline=BASE, tracked_count=len(baseline['tracked']), unrelated_count=len(baseline['unrelated']), changed=changed, unrelated_changed=unrelated, status='PASS' if not changed and not unrelated else 'FAIL', databases_opened=False, tdx_writes=False)
    write('reports/r27/PROTECTED_BYTES.json', result)
    assert result['status']=='PASS', result
    return result


def regression(directory, label):
    from reports.r26.run_regression import scope
    directory = Path(directory).resolve()
    assert directory.drive.upper() in ('E:','F:')
    temp = Path('E:/codex_tmp/test_temp')/('r27-'+label)
    env = dict(os.environ, TEMP=str(temp.parent), TMP=str(temp.parent), TMPDIR=str(temp.parent), PYTHONDONTWRITEBYTECODE='1', PYTHONPATH='src'+os.pathsep+'.', PYTHONIOENCODING='utf-8', WORKBENCH_API_BACKEND='duckdb', WORKBENCH_PG_DSN='dbname=r27_mock host=127.0.0.1 port=1 connect_timeout=1')
    tests = scope()+['tests/test_v4_17_shadow_ui.py','tests/test_v4_18_migration_contract.py']
    capture = temp.parent/('r27-'+label+'.xml')
    command = [sys.executable,'-m','pytest',*tests,'-q','--basetemp='+str(temp),'--junitxml='+str(capture)]
    result = subprocess.run(command,cwd=directory,env=env,capture_output=True)
    raw = capture.read_bytes()
    prefix = 'reports/r27/'+label
    write(prefix+'-tests.xml', raw.decode('utf8'))
    write(prefix+'-output.txt', (result.stdout+result.stderr).decode('utf8'))
    tree = ET.fromstring(raw)
    cases = tree.findall('.//testcase')
    failures = [t.get('classname')+'::'+t.get('name') for t in cases if t.find('failure') is not None]
    inherited = {'tests.upgrade_v3.test_v3_unified_entry::test_v3_is_the_single_unified_workbench_entry','tests.upgrade_v3.test_p01_01_lock_scope::test_hot_rank_route_skips_request_scope','tests.upgrade_v3.test_p01_01_lock_scope::test_send_marks_disconnected_client_closed'}
    errors = len(tree.findall('.//error')); skipped = len(tree.findall('.//skipped'))
    summary = dict(directory=str(directory), source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=directory,text=True).strip(), scope=tests, tests=len(cases), passed=len(cases)-len(failures)-errors-skipped, failures=failures, errors=errors, skipped=skipped, deselected=0, exit_code=result.returncode, temporary_directory=str(temp), captured_xml_sha256=hashlib.sha256(raw).hexdigest(), captured_output_sha256=hashlib.sha256(result.stdout+result.stderr).hexdigest(), status='PASS_SCOPED_NO_NEW_FAILURES' if set(failures)==inherited and errors==skipped==0 else 'FAIL', historical_debt='R26_A01_EXTERNAL_OPEN_NONBLOCKING; NO_TEST_MODIFICATION_OR_DESELECTION')
    write(prefix+'-summary.json', summary)
    assert summary['status']=='PASS_SCOPED_NO_NEW_FAILURES', summary
    print(json.dumps({k:v for k,v in summary.items() if k!='scope'},ensure_ascii=False), flush=True)
    return summary


def seal(source):
    protected = check_protected()
    contract = json.loads((ROOT/'config/v4_18_migration_replay_contract_v1.json').read_text(encoding='utf8'))
    # Evidence cross-check independently re-reads frozen definitions instead of trusting builder output.
    bindings = {}
    for path in sorted((ROOT/'reports/r27').glob('*.json')):
        value = json.loads(path.read_text(encoding='utf8'))
        if 'section' in value:
            assert value['definition'] == contract[value['section']]
            assert value['contract_sha256'] == sha(ROOT/'config/v4_18_migration_replay_contract_v1.json')
            bindings[path.name] = 'EXACT_CONTRACT_SECTION_AND_DIGEST'
    assert len(bindings)==9
    clean = json.loads((ROOT/'reports/r27/clean-summary.json').read_text(encoding='utf8'))
    local = json.loads((ROOT/'reports/r27/local-summary.json').read_text(encoding='utf8'))
    assert clean['source_commit']==source
    assert clean['tests']==local['tests']==245
    write('reports/r27/LOCAL_TEST_SUMMARY.json',local)
    write('reports/r27/CLEAN_REGRESSION.json',clean)
    write('reports/r27/MIGRATION_CONTRACT_GATE.json',dict(status='PASS_LOCAL_READY_FOR_EXTERNAL_AUDIT', scope='STATIC_CONTRACT_DESIGN_COMPLETENESS_ONLY', evidence_bindings=bindings, matrix_rows=len(contract['namespace_matrix']), vectors=20, future_interfaces=6, protected=protected['status'], implementation_entry='BLOCKED_WAIT_REAL_SHADOW_GATE', migration_replay_pass='NOT_GRANTED', next_stage=contract['next_stage']))
    write('docs/evidence/r27/R27_CONTRACT_DESIGN_ACCEPTANCE.md', '# R27 V4-18 Migration Replay contract design\n\nBaseline: `'+BASE+'`. Tested source: `'+source+'`.\n\nR26 scoped engineering acceptance is carried from the supplied external audit. This local result covers contract design only; it grants no real Shadow readback, migration implementation, production Focus cutover, accepted V4-18 head or MIGRATION_REPLAY_PASS.\n\nThe namespace matrix inventories every repository SQL table declaration and explicitly separates declaration coverage from actual deployed storage authority. Native snapshot binding and user-work export remain future independently accepted inputs. Semantic carry mappings preserve predecessor/model lineage, original episodes/enrollment, frozen T0 controls/benchmarks, due obligations, outcome revisions and user ownership. Historical Shadow context remains immutable. Exact snapshot/final watermarks reconcile Legacy and Shadow gaps; rollback restores routing and retains accepted facts, user work and settlement ownership.\n\nM01–M20 are declarative future runtime acceptance vectors. Six interfaces are frozen as design definitions with no production implementation. All five implementation-entry receipts remain absent; entry is BLOCKED_WAIT_REAL_SHADOW_GATE.\n\nValidation: 24 static contract checks plus 221 existing UI/Focus checks; 242 passed and the same three R26-A01 historical failures remained. No tests were changed or deselected to hide those failures. The first authoring check found an incorrect test cardinality assumption about grouped rollback retention; the assertion now checks the required semantic set. No migration runtime was tested or executed. All pre-existing tracked files and unrelated work were verified unchanged. Temporary checkouts, pytest captures and caches use E:.\n\nNEXT: STOP_WAIT_R27_INDEPENDENT_EXTERNAL_AUDIT. Commit and push provide a reviewable candidate, not external acceptance.\n')
    files = [p for base in ('reports/r27','docs/evidence/r27') for p in (ROOT/base).rglob('*') if p.is_file() and p.suffix not in ('.pyc',) and p.name!='R27_CONTRACT_CANDIDATE_SEAL.json']
    files += [ROOT/'config/v4_18_migration_replay_contract_v1.json', ROOT/'tests/test_v4_18_migration_contract.py']
    write('reports/r27/R27_CONTRACT_CANDIDATE_SEAL.json',dict(tested_source_commit=source, baseline=BASE, tested_tag='codex/r27-migration-contract-tested-source-20261004', source_scope='ADDITIVE_CONTRACT_TEST_AND_EVIDENCE_ONLY', files={p.relative_to(ROOT).as_posix():sha(p) for p in files}, status='LOCAL_CONTRACT_CANDIDATE_NOT_EXTERNAL_ACCEPTANCE', next_stage='STOP_WAIT_R27_INDEPENDENT_EXTERNAL_AUDIT'))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['local','clean','seal','protected']);parser.add_argument('--directory',default=str(ROOT));parser.add_argument('--source');args=parser.parse_args()
    if args.mode in ('local','clean'): regression(args.directory,args.mode)
    elif args.mode=='seal': seal(args.source)
    else: check_protected()
