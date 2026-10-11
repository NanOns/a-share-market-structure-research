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
LEGACY_AST_NODE='tests/test_v4_17_shadow_ui.py::test_legacy_module_ast_identical_after_removing_additive_shadow_routes'
DYNAMIC_CAPABILITY_MODULES={
    'adjustment.tdx_adjustment_v0_3','workbench_analysis.dm01_incremental_component_builders_r3_3',
    'workbench_analysis.r43_owner_replay','workbench_service.core_product_bff_r1',
    'workbench_service.stock_views','workbench_service.production_v4','workbench_service.research_bff',
    'workbench_analysis.operational_daily_jobs_pg_r1','workbench_analysis.operational_daily_jobs_v1',
    'workbench_desktop.engine','workbench_db.v4_history_pg_r1','workbench_db.v4_snapshot_pg_r2',
    'workbench_db.v4_series_pg_r1','workbench_db.v4_journal_pg_r1','workbench_service.shadow_context',
    'focus_tracker.v4_daily_driver','focus_tracker.v4_path_adapter',
    # Actual daily producer and exact transport invoke these version-neutral
    # decoding/formula leaves. Their standalone numerical/negative tests are
    # V4 dependencies even when their filenames predate V4.
    'adjustment.tdx_adjustment','tdx.day_reader','tdx.gbbq_reader',
    'market_calendar.trading_calendar','workbench_analysis.operational_daily_calendar_v2',
    'workbench_analysis.operational_daily_periods_v1',
}

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
        if row['canonical_nodeid']==LEGACY_AST_NODE:
            row.update(r3_legal_disposition='LEGACY_ONLY_EXCLUDED',
                r3_close_condition='Pure V3 app AST identity to historical 60b175 source, independently partitioned from native V4 shadow HTTP tests; original result preserved')
    write_rows(rows)
    emit('V4_TEST_LEGAL_SCOPE_FINAL.json', dict(contract_id='R4_R3_LEGAL_SCOPE_R1', status='NOT_FINAL_ADMISSION_OPEN',
        global_v4_legal_denominator=None, preserved_original_nodes=4568, original_counts=counts,
        baseline_execution_modules=sorted(original), additional_candidate_modules=[m['path'] for m in modules if m['nominated_for_review'] and not m['original_included']],
        exclusion_rule='Only documented independent old capability with no supported V4 runtime/capability dependency; filename alone is insufficient',
        certification_conditions=['Every nomination reviewed against current normative capability and dynamic evidence', 'Every original stable node retains prior outcome', 'All admitted nodes collected and replayed on one frozen source and clean PG', 'All exclusions independently reviewable'],
        prohibited=['shrinking historical denominator', 'inferring dynamic reachability from AST', 'declaring missing engineering fixtures a future-time gate']))
    emit('EXPLICIT_LEGACY_NODE_REVIEW.json',dict(contract_id='R4_R3_SINGLE_NODE_LEGACY_REVIEW_R1',
        nodeid=LEGACY_AST_NODE,decision='LEGACY_ONLY_EXCLUDED',
        contract='Requires entire workbench_service.app V3 AST identical to frozen historical source; no current V4 business numerical assertion',
        current_v4_replacement_evidence='Native V4 shadow_server real HTTP normal and bad-contract tests remain admitted; only this single old AST identity node is excluded',
        retained_original_outcome=True,review_owner='root / P0-1',source_sha256=digest(ROOT/'tests/test_v4_17_shadow_ui.py')))
    # Admit direct tests of the capabilities actually exercised in the real
    # HTTP/desktop/worker trace. File names (including old directory names)
    # cannot admit or exclude a test independently of its called capability.
    additions={m['path'] for m in modules if set(m['direct_imports']) & DYNAMIC_CAPABILITY_MODULES}
    additions.update(m['path'] for m in modules if m['normative_v4_import_candidates'] and '/upgrade_v3/' not in m['path'])
    additions.update(p for p in ('tests/test_v4_exact_candidate_gate_r3.py','tests/test_v4_exact_period_quality_r3.py',
        'tests/test_operational_daily_periods_v1.py','tests/test_v4_exact_transport_r4.py',
        'tests/test_v4_pg_runtime_consumers_r3.py','tests/test_v4_exact_focus_path_r3.py',
        'tests/test_v4_joint_streaming_source_r3.py','tests/test_v4_product_transport_r3.py',
        'tests/test_engineering_pg_publication_r3.py','tests/test_v4_legacy_api_dynamic_boundary_r3.py',
        'tests/test_v4_request_snapshot_scope_r3.py','tests/test_v4_native_source_scope_r3.py',
        'tests/test_r4_r3_input_recovery.py','tests/test_v4_current_owner_contracts_r3.py',
        'tests/test_v4_exact_operational_core_r3.py') if (ROOT/p).exists())
    selected=sorted(original|additions)
    emit('V4_EXPANDED_EXECUTION_MODULES_R1.json',dict(contract_id='R4_R3_DYNAMIC_CAPABILITY_TEST_EXPANSION_R1',
        modules=selected,original_modules=len(original),added_modules=sorted(additions-original),
        dynamic_capability_modules=sorted(DYNAMIC_CAPABILITY_MODULES),
        evidence=['../r4_r3_semantics_http_20261011/DYNAMIC_CONSUMER_TRACE.json','../r4_r3_consumers_20261011/V4_ALL_REAL_CONSUMERS.csv'],
        status='EXECUTION_EXPANSION_LEGAL_GLOBAL_COMPLETENESS_REVIEW_OPEN',
        limitations=['Unobserved conditional 56-consumer paths are not excluded; global completeness still requires supported dynamic capability review']))
    return selected

def write_rows(rows):
    target = OUT / 'TEST_NODE_DISPOSITION_FINAL.csv'
    temp = target.with_suffix('.csv.tmp')
    with temp.open('w', encoding='utf8', newline='') as stream:
        writer = csv.DictWriter(stream, list(rows[0])); writer.writeheader(); writer.writerows(rows)
    os.replace(temp, target)

def replay(collect=False):
    files = build()
    name = ('BASELINE_COLLECTION_' if collect else 'V4_BASELINE_FULL_GUARDED_') + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')
    binding_snapshot=name+'_SOURCE_BINDINGS.json'
    (OUT/binding_snapshot).write_bytes((OUT/'SOURCE_BINDINGS.json').read_bytes())
    env = dict(os.environ, TMP='G:/codex_tmp', TEMP='G:/codex_tmp', TMPDIR='G:/codex_tmp', PYTHONDONTWRITEBYTECODE='1',
               PYTHONUTF8='1', PYTHONPATH=os.pathsep.join(['G:/codex_tmp/r4_r3_python_deps',str(ROOT / 'src'), str(ROOT)]), R4_NATIVE_ISOLATION='1',
               R4_PG_DATA_DIRECTORY='G:/codex_tmp/full_system_r4_fbd23a6b/pg_data', R4_CONNECTION_LEDGER=str(OUT / (name + '_CONNECTIONS.jsonl')))
    if not env.get('V4_NATIVE_PG_DSN'): raise ValueError('EXPLICIT_ISOLATED_PG_DSN_REQUIRED')
    # Native test capability manifest attests the disposable FEP cluster and
    # all 33 SQL migrations before the plugin grants any connection.
    fep_dsn='host=127.0.0.1 port=55792 user=r4_isolated_admin dbname=fep_e1_fresh connect_timeout=5'
    env.update(FEP_E1_TEST_DSN=fep_dsn,FEP_E5_TEST_DSN=fep_dsn,WORKBENCH_PG_DSN=fep_dsn,V4_10_DISPOSABLE_TEST_DSN=fep_dsn,
               R4_PG_TEST_CAPABILITIES=str(ROOT/'docs/audits/full_system_r4_pg_only_20261011_fbd23a6b/R4_PG_TEST_CAPABILITIES.json'),
               OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='2',MKL_NUM_THREADS='2')
    extra=OUT/'R3_EXTRA_PG_FIXTURES.json'
    canonical=OUT/'FEP_CANONICAL_FIXTURE_SOURCE_BINDINGS_R1.json'
    if extra.exists() and canonical.exists():
        env.update(R4_R3_EXTRA_PG_FIXTURES=str(extra),FEP_E5_CANONICAL_TEST_ENABLE='1',
                   FEP_AUTHORITY_TEST_DSN='host=127.0.0.1 port=55793 user=r4_isolated_admin dbname=fep_authority_isolated')
    xml = OUT / (name + '.xml')
    command = [sys.executable, '-B', '-m', 'pytest', '-q', *files,
               '--basetemp=G:/codex_tmp/test_temp/r4_r3_scope_' + name,
               '-o', 'cache_dir=G:/codex_tmp/pytest_cache_r4_r3_scope', '--junitxml=' + str(xml), '--continue-on-collection-errors',
               '--deselect='+LEGACY_AST_NODE]
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
    collected_path=OUT/(name+'_CONNECTIONS_COLLECTED_NODES.json')
    collected=json.loads(collected_path.read_bytes()) if collected_path.is_file() else None
    emit(name + '_RESULT.json', dict(exit_code=result.returncode, command=command, seconds=time.time() - started,
         counts=counts, current_unique_nodes=len(current), baseline_modules=len(files),
         collected_nodes=len(collected['nodes']) if collected else None,
         collected_node_set_sha256=digest(collected_path) if collected else None,
         collection_only=collect,
         source_binding=binding_snapshot, source_binding_sha256=digest(OUT / binding_snapshot),
         status='RAW_BASELINE_REPLAY_ONLY_LEGAL_ADMISSION_AND_CLEAN_SLATE_NOT_CERTIFIED',
         limitations=['Inherited historical fixture hooks intentionally not auto-loaded', 'Baseline replay is not the certified complete legal denominator', 'All failed nodes and collection faults retained']))
    print(json.dumps(dict(counts=counts, exit_code=result.returncode, seconds=time.time() - started)))
    return result.returncode

if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--run', action='store_true'); parser.add_argument('--collect', action='store_true')
    args = parser.parse_args()
    raise SystemExit(replay(args.collect) if args.run or args.collect else (build() and 0))
