"""R3 continuation scope ledger: retain every baseline outcome, never infer admission.

Static imports nominate review candidates; runtime and normative evidence are
required independently before the legal denominator can be certified.
"""
import argparse
import ast
import csv
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from datetime import datetime, timezone
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/audits/r4_r3_scope_20261011'
BASE = ROOT / 'config/v4_audit_regression_scope_r3.json'

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def emit(name, value):
    OUT.mkdir(parents=True, exist_ok=True)
    target = OUT / name
    temp = target.with_suffix(target.suffix + '.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    os.replace(temp, target)

def imports(path):
    tree = ast.parse(path.read_text('utf-8-sig'))
    return sorted({n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module} |
                  {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names})

def canonical(node):
    """pytest JUnit classname uses dots; parameters and classes stay intact."""
    module, name = node.split('::', 1)
    return module.replace('.', '/') + '.py::' + name

def failure_category(message):
    if 'NON_POSTGRES' in message or 'SQLITE_FORBIDDEN' in message or 'DUCKDB_FORBIDDEN' in message:
        return 'NON_PG_BACKEND_ATTEMPT'
    if 'UNATTESTED_PG' in message or 'DSN' in message or 'DISPOSABLE_PG' in message:
        return 'PG_FIXTURE_OR_PERMISSION'
    if 'FileNotFoundError' in message or 'MISSING' in message or 'SOURCE_INCOMPLETE' in message:
        return 'SOURCE_FIXTURE_REVIEW_REQUIRED'
    return 'BUSINESS_OR_HARNESS_REVIEW_REQUIRED'

def build():
    baseline = json.loads(BASE.read_bytes())
    graph_path = ROOT / 'docs/audits/full_system_r4_pg_only_20261011_fbd23a6b/V4_RUNTIME_CALL_GRAPH_R4.json'
    reached = set(json.loads(graph_path.read_bytes())['candidate_modules'])
    original = {x['path'] for x in baseline['included_test_modules']}
    modules = []
    for p in sorted((ROOT / 'tests').rglob('test_*.py')):
        path = p.relative_to(ROOT).as_posix()
        direct = imports(p)
        matches = [m for m in direct if m in reached]
        normative_v4 = [m for m in direct if m.startswith(('v4.', 'workbench_analysis.fep_', 'workbench_db.v4_', 'workbench_service.v4_'))]
        nomination = path in original or bool(matches) or bool(normative_v4)
        modules.append(dict(path=path, sha256=digest(p), original_included=path in original,
                            direct_imports=direct, static_runtime_candidates=matches,
                            normative_v4_import_candidates=normative_v4,
                            nominated_for_review=nomination,
                            legal_disposition='ADMISSION_REVIEW_REQUIRED' if nomination else 'EXCLUSION_REVIEW_REQUIRED',
                            owner='P0-1', dynamic_proof='OPEN', normative_proof='OPEN',
                            reason='Baseline membership and imports are nominations, never proof of legal admission or exclusion'))
    frozen = {p.relative_to(ROOT).as_posix(): digest(p) for base in ('src', 'scripts', 'tests') for p in (ROOT / base).rglob('*.py')}
    frozen.update({p: digest(ROOT / p) for p in ('conftest.py', 'run_workbench_service.py', 'run_desktop.py')})
    emit('SOURCE_BINDINGS.json', dict(git_head=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                                    source_files=frozen, source_tree_sha256=hashlib.sha256(json.dumps(frozen, sort_keys=True).encode()).hexdigest(),
                                    meaning='Exact bytes before this run; HEAD is not substituted for dirty source bytes'))
    emit('V4_MODULE_LEGAL_SCOPE_REVIEW.json', dict(contract_id='R4_R3_LEGAL_SCOPE_REVIEW_R1',
          modules=modules, baseline_modules=len(original), nominated_modules=sum(m['nominated_for_review'] for m in modules),
          legal_denominator=None, status='REVIEW_OPEN', deletion_or_deselection=[],
          input_scope_sha256=digest(BASE), static_graph_sha256=digest(graph_path)))
    rows = list(csv.DictReader((ROOT / 'docs/audits/r4_external_repair_r2_20261011/TEST_NODE_DISPOSITION_R2.csv').open(encoding='utf-8-sig')))
    if len(rows) != 4568 or len({r['nodeid'] for r in rows}) != 4568:
        raise ValueError('BASELINE_NODE_IDENTITY_OR_COUNT_DRIFT')
    counts = {k: sum(r['previous_result'] == k for r in rows) for k in ('PASS', 'FAIL', 'ERROR', 'SKIP')}
    if counts != dict(PASS=3810, FAIL=237, ERROR=209, SKIP=312):
        raise ValueError('BASELINE_OUTCOME_DRIFT')
    for row in rows:
        row.update(canonical_nodeid=canonical(row['nodeid']), r3_current_result='NOT_RUN',
                   r3_legal_disposition='ADMISSION_REVIEW_REQUIRED', r3_first_failure_category='',
                   r3_current_evidence='', r3_close_condition='Normative contract and supported runtime proof; guarded replay and independent oracle')
    write_rows(rows)
    emit('V4_TEST_LEGAL_SCOPE_FINAL.json', dict(contract_id='R4_R3_LEGAL_SCOPE_R1', status='NOT_FINAL_ADMISSION_OPEN',
        global_v4_legal_denominator=None, preserved_original_nodes=4568, original_counts=counts,
        baseline_execution_modules=sorted(original), additional_candidate_modules=[m['path'] for m in modules if m['nominated_for_review'] and not m['original_included']],
        exclusion_rule='Only documented independent old capability with no supported V4 runtime/capability dependency; filename alone is insufficient',
        certification_conditions=['Every nomination reviewed against current normative capability and dynamic evidence', 'Every original stable node retains prior outcome', 'All admitted nodes collected and replayed on one frozen source and clean PG', 'All exclusions independently reviewable'],
        prohibited=['shrinking historical denominator', 'inferring dynamic reachability from AST', 'declaring missing engineering fixtures a future-time gate']))
    return sorted(original)

def write_rows(rows):
    target = OUT / 'TEST_NODE_DISPOSITION_FINAL.csv'
    temp = target.with_suffix('.csv.tmp')
    with temp.open('w', encoding='utf8', newline='') as stream:
        writer = csv.DictWriter(stream, list(rows[0])); writer.writeheader(); writer.writerows(rows)
    os.replace(temp, target)

def replay(collect=False):
    files = build()
    name = ('BASELINE_COLLECTION_' if collect else 'V4_BASELINE_FULL_GUARDED_') + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')
    env = dict(os.environ, TMP='G:/codex_tmp', TEMP='G:/codex_tmp', TMPDIR='G:/codex_tmp', PYTHONDONTWRITEBYTECODE='1',
               PYTHONUTF8='1', PYTHONPATH=os.pathsep.join([str(ROOT / 'src'), str(ROOT)]), R4_NATIVE_ISOLATION='1',
               R4_PG_DATA_DIRECTORY='G:/codex_tmp/full_system_r4_fbd23a6b/pg_data', R4_CONNECTION_LEDGER=str(OUT / (name + '_CONNECTIONS.jsonl')))
    if not env.get('V4_NATIVE_PG_DSN'): raise ValueError('EXPLICIT_ISOLATED_PG_DSN_REQUIRED')
    xml = OUT / (name + '.xml')
    command = [sys.executable, '-B', '-m', 'pytest', '-q', *files,
               '--basetemp=G:/codex_tmp/test_temp/r4_r3_scope_' + name,
               '-o', 'cache_dir=G:/codex_tmp/pytest_cache_r4_r3_scope', '--junitxml=' + str(xml), '--continue-on-collection-errors']
    if collect: command.append('--collect-only')
    started = time.time()
    with (OUT / (name + '.log')).open('w', encoding='utf8') as log:
        result = subprocess.run(command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
    cases = ET.parse(xml).findall('.//testcase') if xml.exists() else []
    current = {}
    for case in cases:
        status = 'FAIL' if case.find('failure') is not None else 'ERROR' if case.find('error') is not None else 'SKIP' if case.find('skipped') is not None else 'PASS'
        node = case.get('classname', '') + '::' + case.get('name', '')
        fault = case.find('failure')
        if fault is None: fault = case.find('error')
        message = '' if fault is None else (fault.get('message', '') + '\n' + (fault.text or ''))
        current[node] = (status, failure_category(message) if status in ('FAIL', 'ERROR') else '', message)
    if not collect:
        rows = list(csv.DictReader((OUT / 'TEST_NODE_DISPOSITION_FINAL.csv').open(encoding='utf8')))
        for row in rows:
            status, category, _ = current.get(row['nodeid'], ('NOT_RUN_OR_COLLECTION_DRIFT', '', ''))
            row.update(r3_current_result=status, r3_first_failure_category=category, r3_current_evidence=xml.name)
        write_rows(rows)
    counts = {s: sum(x[0] == s for x in current.values()) for s in ('PASS', 'FAIL', 'ERROR', 'SKIP')}
    emit(name + '_RESULT.json', dict(exit_code=result.returncode, command=command, seconds=time.time() - started,
         counts=counts, current_unique_nodes=len(current), baseline_modules=len(files),
         source_binding='SOURCE_BINDINGS.json', source_binding_sha256=digest(OUT / 'SOURCE_BINDINGS.json'),
         status='RAW_BASELINE_REPLAY_ONLY_LEGAL_ADMISSION_AND_CLEAN_SLATE_NOT_CERTIFIED',
         limitations=['Inherited historical fixture hooks intentionally not auto-loaded', 'Baseline replay is not the certified complete legal denominator', 'All failed nodes and collection faults retained']))
    print(json.dumps(dict(counts=counts, exit_code=result.returncode, seconds=time.time() - started)))
    return result.returncode

if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--run', action='store_true'); parser.add_argument('--collect', action='store_true')
    args = parser.parse_args()
    raise SystemExit(replay(args.collect) if args.run or args.collect else (build() and 0))
