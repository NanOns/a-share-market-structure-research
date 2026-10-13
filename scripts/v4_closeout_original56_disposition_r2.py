"""Render a bounded disposition from preserved ORIGINAL56 and runtime receipts."""
import csv
import hashlib
import os
import json
import tempfile
from pathlib import Path
from workbench_analysis.operational_daily_storage_v1 import atomic_json

ROOT = Path(__file__).resolve().parents[1]
WORK = Path('G:/codex_tmp/v4_full_closeout_20261012')
EVIDENCE = ROOT / 'docs/audits/v4_full_closeout_20261012/continuation_20261013/ORIGINAL56_DISPOSITION_R2'
OLD = ROOT / 'docs/audits/v4_full_closeout_20261012/continuation_20261013/ORIGINAL56_DISPOSITION_R1'
GRAPH = WORK / 'ORIGINAL56_REACHABILITY_R4.json'
HTTP = WORK / 'CURRENT_SOURCE_CANDIDATE_HTTP_R6_R1'
TRACE = HTTP / 'EXACT56_TRACE.json'
RESULT = HTTP / 'RESULT.json'
HISTORICAL = {'src/workbench_analysis/dm01_incremental_component_builders.py'}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic_bytes(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=path.parent, prefix=path.name + '.', suffix='.tmp')
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data); stream.flush(); os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def main():
    expected_outputs = {'MATRIX.json', 'MATRIX.csv', 'RESULT.json', 'DYNAMIC_SITES.json'}
    if EVIDENCE.exists():
        if any(p.name not in expected_outputs for p in EVIDENCE.iterdir()):
            raise ValueError('PRESERVE_EXISTING_R2_EVIDENCE')
        existing_result = EVIDENCE / 'RESULT.json'
        if existing_result.exists() and json.loads(existing_result.read_bytes()).get('contract_id') != 'V4_ORIGINAL56_BOUNDED_CURRENT_ENTRY_DISPOSITION_R2':
            raise ValueError('PRESERVE_DIFFERENT_R2_EVIDENCE')
    graph = json.loads(GRAPH.read_bytes())
    prior = json.loads((OLD / 'RESULT.json').read_bytes())
    http = json.loads(RESULT.read_bytes())
    http_trace = json.loads(TRACE.read_bytes())
    assert graph['denominator'] == prior['denominator'] == http_trace['denominator'] == 56
    assert graph['contract_id'] == 'V4_ORIGINAL56_CURRENT_REACHABILITY_AUDIT_R4'
    assert http['acceptance'] == 'PASS_CURRENT_HTTP_SCOPE' and http['publication'] is False
    graph_rows = {row['path']: row for row in graph['rows']}
    http_rows = {row['path']: row for row in http_trace['rows']}
    prior_rows = list(csv.DictReader((OLD / 'MATRIX.csv').open(encoding='utf-8-sig', newline='')))
    files = {x['path']: x for x in graph['reachable_files']}
    rows = []
    for old in prior_rows:
        path = old['path']
        g = graph_rows[path]
        current = ROOT / path
        if sha(current) != old['source_sha256'] or g['current_source']['sha256'] != old['source_sha256']:
            raise ValueError(f'SOURCE_IDENTITY_DRIFT:{path}')
        h = http_rows[path]
        if h['source_sha256'] != old['source_sha256']:
            raise ValueError(f'HTTP_TRACE_SOURCE_IDENTITY_DRIFT:{path}')
        if path in HISTORICAL:
            disposition = 'HISTORICAL_ONLY'
            role = 'IMPORTED_FOR_HISTORICAL_REGISTRY_VALIDATION_NO_CURRENT_FUNCTION_CALL'
            reason = 'Exact current daily trace records zero calls; current bounded business builder is the versioned r3_3 module.'
        elif g['static_reachable']:
            disposition = 'ACTIVE_REACHABLE'
            role = old['role']
            reason = 'Reachable from one of four fixed entries; source hash matches and bounded execution observations are retained.'
            if not g['observations'] and role != 'PACKAGE_EXPORTS_ONLY':
                raise ValueError(f'REACHABLE_WITHOUT_FUNCTION_EVIDENCE:{path}')
        else:
            disposition = 'NOT_REACHABLE_WITH_PROOF'
            role = 'OUTSIDE_CLOSED_CURRENT_ENTRY_GRAPH'
            reason = 'Absent from conservative import closure after reviewing every recorded dynamic site and its fixed target/allowlist.'
        calls = []
        for obs in g['observations']:
            calls.append(dict(trace=obs['trace'], executed_source_sha256=obs['executed_source_sha256'],
                              current_file_same=obs['current_file_same'], functions=[c['function'] for c in obs['calls']],
                              call_counts={c['function']: c['calls'] for c in obs['calls']}))
        if h['actual_call_count']:
            calls.append(dict(trace='CURRENT_SOURCE_CANDIDATE_HTTP_R6_R1/EXACT56_TRACE.json',
                              executed_source_sha256=h['source_sha256'], current_file_same=h['source_unchanged_during_run'],
                              functions=[c['function'] for c in h['calls']],
                              call_counts={c['function']: c['calls'] for c in h['calls']}))
        rows.append(dict(path=path, source_sha256=old['source_sha256'], disposition=disposition, role=role,
                         reason=reason, static_reachable=g['static_reachable'], witness=g['witness'],
                         current_entry_call_count=h['actual_call_count'], current_entry_classification=h['classification'],
                         calls=calls, business_numeric_acceptance='RETAINED_PRIOR_SCOPED_RECEIPTS; RELEASE_GATE_REQUIRES_STAGE3_PG_CONSUMER_JOIN'))
    counts = {name: sum(r['disposition'] == name for r in rows) for name in
              ('ACTIVE_REACHABLE', 'HISTORICAL_ONLY', 'RETIRED', 'NOT_REACHABLE_WITH_PROOF')}
    if sum(counts.values()) != 56 or counts != dict(ACTIVE_REACHABLE=20, HISTORICAL_ONLY=1, RETIRED=0, NOT_REACHABLE_WITH_PROOF=35):
        raise ValueError(f'DISPOSITION_COUNTS:{counts}')
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    atomic_json(ROOT, EVIDENCE / 'MATRIX.json', rows)
    fields = ['path', 'source_sha256', 'disposition', 'role', 'static_reachable', 'current_entry_call_count',
              'current_entry_classification', 'witness', 'reason', 'business_numeric_acceptance']
    import io
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=fields); writer.writeheader()
    for row in rows:
        values = dict(row, witness=' -> '.join(row['witness'] or []))
        writer.writerow({key: values[key] for key in fields})
    atomic_bytes(EVIDENCE / 'MATRIX.csv', ('\ufeff' + stream.getvalue()).encode('utf-8'))
    dynamic = []
    for module, sites in graph['dynamic_sites'].items():
        for site in sites:
            expression = site['expression']
            if "__import__('time')" in expression or "__import__('zoneinfo')" in expression or "__import__('json')" in expression or "__import__('os')" in expression or "__import__('getpass')" in expression or "__import__('sys')" in expression:
                review = 'FIXED_STANDARD_LIBRARY_MODULE'
            elif 'source_adapter.py' in module and 'builtins.__import__(name' in expression:
                review = 'FIXED_CALLSITE_ALLOWLIST; other resolved imports are directly represented in static AST edges'
            elif 'spec_from_file_location' in expression or 'exec_module' in expression:
                review = 'FIXED_REPOSITORY_PATH_AND_MODULE_NAME'
            elif 'exec(compile' in expression:
                review = 'BOUNDED_IN_MEMORY_AST_OR_FIXED_CONTRACT; no external module or arbitrary path target'
            else:
                raise ValueError(f'UNREVIEWED_DYNAMIC_SITE:{module}:{site}')
            dynamic.append(dict(module=module, **site, review=review))
    manifest = dict(contract_id='V4_ORIGINAL56_BOUNDED_CURRENT_ENTRY_DISPOSITION_R2',
        acceptance='PASS_CLASSIFICATION_ONLY', denominator=56, counts=counts,
        entries=graph['entries'], graph_sha256=sha(GRAPH), prior_disposition_sha256=sha(OLD / 'MATRIX.csv'),
        current_source_http_result_sha256=sha(RESULT), current_source_http_trace_sha256=sha(TRACE),
        dynamic_site_count=len(dynamic), dynamic_sites_reviewed=dynamic,
        source_identity_drift=0, unknown=0,
        scope='Four fixed desktop/server/executor/source-adapter roots and the exact R6 current-candidate HTTP request; this classifies reachability only. It does not assert full numerical or production acceptance. Each active item keeps source function trace and its numerical/PG join remains an explicit next-stage release gate.',
        current_source_http={k: http[k] for k in ('acceptance', 'T0', 'records', 'checks', 'reader_role', 'port', 'server_stopped', 'publication', 'production_cutover')},
        next_stage='Join every ACTIVE_REACHABLE item to accepted PG objects, field-level oracle, and the corresponding business HTTP/page output; then close daily publication and final regression gates.')
    atomic_json(ROOT, EVIDENCE / 'RESULT.json', manifest)
    atomic_json(ROOT, EVIDENCE / 'DYNAMIC_SITES.json', dynamic)
    print(json.dumps(dict(acceptance=manifest['acceptance'], counts=counts, dynamic_sites=len(dynamic), unknown=0)))


if __name__ == '__main__':
    main()
