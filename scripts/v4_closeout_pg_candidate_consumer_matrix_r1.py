"""Reconcile preserved exact56, PG, field and HTTP receipts for one candidate."""
import csv
import hashlib
import io
import json
import os
import tempfile
from pathlib import Path
from workbench_analysis.operational_daily_storage_v1 import atomic_json

ROOT = Path('G:/codex work/v4-production-20261012')
WORK = Path('G:/codex_tmp/v4_full_closeout_20261012')
AUDIT = Path('G:/codex work/v4-full-closeout-20261012/docs/audits/v4_full_closeout_20261012')
OUT = AUDIT / 'continuation_20261013/PG_CURRENT_CANDIDATE_CONSUMER_R1'
CANDIDATE_SHA = '0f5c3589887e08d1571b69c4fca4a9b0393f2b2d2e1ebcfd1f35cbb16ce7b79a'
OLD_CANDIDATE_SHA = '5e982bfaea54215472b3baefbd7a3a58fa7fa6251039efdb86c7634e6edb8c44'

EVIDENCE = {
    'CORE_VERSION': AUDIT/'continuation_20261013/CORE_VERSION_CONSERVATION_R1/CORE_VERSION_CONSERVATION_R1.json.gz',
    'CORE_UNCOVERED': WORK/'CORE_UNCOVERED_NUMERIC_ORACLE_R6_R1.json',
    'SECTOR': WORK/'FULL_CURRENT_SECTOR_NUMERIC_ORACLE_R6_R1.json',
    'RELATIVE': WORK/'RELATIVE_MARKET_NUMERIC_ORACLE_R6_R1.json',
    'LOO': WORK/'FULL_CURRENT_LOO_NUMERIC_ORACLE_R6_R1.json',
    'DAILY_PERIOD': WORK/'DAILY_PERIOD_ORACLE_R6.json',
    'PROFILE_RULE': WORK/'PROFILE_FULL_RULE_ORACLE_R6_R1.json',
    'FIELD_ORIGINAL': WORK/'FIELD_PROJECTION_ORACLE_R6_R1/RESULT.json',
    'FIELD_COVERAGE': WORK/'FIELD_PROJECTION_FAILURE_COVERAGE_R6_R1.json',
    'FIELD_CONTINUATION': WORK/'FIELD_PROJECTION_RELATIVE_CONTINUATION_R6_R1.json',
    'FOCUS': AUDIT/'continuation_20261013/FORMAL_EXACT_FOCUS_ORACLE_R6/RESULT.json',
    'D1_COUNTER': WORK/'D1_COUNTER_SELECTOR_ORACLE_R6_R1.json',
    'D1_UPSTREAM': WORK/'D1_UPSTREAM_BINDING_ORACLE_R6_R1.json',
    'D1_DIGEST': WORK/'D1_INPUT_DIGEST_ORACLE_R6_R3.json',
    'D1_OTHERWISE': WORK/'D1_OTHERWISE_RULE_CONTINUATION_R6_R3.json',
    'PROFILE_PATCH': AUDIT/'continuation_20261013/PROFILE_NATIVE_PATCH_R1/PROFILE_SEMANTIC_BFF_READBACK_R6_R1.json',
    'PROFILE_DEPENDENTS': AUDIT/'continuation_20261013/PROFILE_DEPENDENT_CLOSEOUT_R1/NATIVE_DEPENDENT_CONSUMER_READBACK_R6_R1.json',
    'MEMBERS': AUDIT/'continuation_20261013/PG_REFERENCE_CONSUMERS_R1/NATIVE_MEMBER_CONSUMER_READBACK_R6.json',
    'IDENTITY': AUDIT/'continuation_20261013/PG_REFERENCE_CONSUMERS_R1/NATIVE_SEARCH_IDENTITY_PREPARATION_R6.json',
    'HTTP': WORK/'CURRENT_SOURCE_CANDIDATE_HTTP_R6_R1/RESULT.json',
    'HTTP_TRACE': WORK/'CURRENT_SOURCE_CANDIDATE_HTTP_R6_R1/EXACT56_TRACE.json',
    'PG_ROLES': AUDIT/'FORMAL_PG_ROLES_R1.json',
    'SOURCE_COMPONENT': WORK/'COMPONENT_SOURCE_CONSERVATION_R6_R1.json',
}

SOURCE_MAP = {
    'src/adjustment/tdx_adjustment.py': ('Core adjusted price', 'CORE_VERSION,CORE_UNCOVERED', 'stocks'),
    'src/adjustment/tdx_adjustment_v0_3.py': ('Exact QFQ Core/Focus coordinates', 'CORE_VERSION,CORE_UNCOVERED,FOCUS', 'stocks,focus'),
    'src/adjustment/__init__.py': ('Versioned adjustment package exports', 'CORE_VERSION', 'stocks'),
    'src/focus_tracker/price_path.py': ('Actual traded Focus/Forward price path', 'FOCUS', 'focus'),
    'src/focus_tracker/v4_native_core_adapter.py': ('Native Focus Core projection adapter', 'FOCUS', 'focus'),
    'src/focus_tracker/v4_path_adapter.py': ('Native Focus price path adapter', 'FOCUS', 'focus'),
    'src/workbench_analysis/corrected_owner_replay.py': ('Bound immutable Owner read/write', 'FIELD_ORIGINAL,FIELD_CONTINUATION', 'stocks,sectors,focus,market'),
    'src/workbench_analysis/dm01_incremental_component_builders_r3_3.py': ('Current exact daily Core/Profile/Sector/period builders', 'CORE_VERSION,CORE_UNCOVERED,DAILY_PERIOD,PROFILE_RULE', 'stocks,sectors,market'),
    'src/workbench_analysis/operational_daily_periods_v1.py': ('Daily RAW/QFQ period projection', 'DAILY_PERIOD', 'stocks,sectors'),
    'src/workbench_analysis/r43_focus_replay.py': ('Focus/Forward daily owner replay', 'FOCUS', 'focus'),
    'src/workbench_analysis/r43_market_replay.py': ('Market and relative sector replay', 'RELATIVE,LOO,SECTOR', 'market,sectors,stocks'),
    'src/workbench_analysis/r43_owner_replay.py': ('Owner source identity and immutable payload', 'FIELD_ORIGINAL,FIELD_CONTINUATION,HTTP_TRACE', 'home,stocks,sectors,focus,market,diagnostics'),
    'src/workbench_analysis/r43_structure_replay.py': ('D1 structure projection', 'D1_COUNTER,D1_UPSTREAM,D1_DIGEST,D1_OTHERWISE', 'focus'),
    'src/workbench_analysis/research_features.py': ('Optional research candidate sidecar', 'SOURCE_COMPONENT', 'candidate_only'),
    'src/workbench_analysis/sector_cycle.py': ('Optional sector-cycle candidate sidecar', 'SECTOR,SOURCE_COMPONENT', 'candidate_only'),
    'src/workbench_analysis/tdx_sector_retro_r43.py': ('Dated TDX member source normalization', 'MEMBERS', 'stocks,sectors'),
    'src/workbench_analysis/v4_12_structure_engine.py': ('Versioned D1 machine/anchor contracts', 'D1_COUNTER,D1_UPSTREAM,D1_DIGEST,D1_OTHERWISE', 'focus'),
    'src/workbench_db/api_connection.py': ('Legacy local API denial boundary', 'HTTP,PG_ROLES', 'guard_only'),
    'src/workbench_service/core_product_bff_r1.py': ('PG-backed current product projections', 'FIELD_ORIGINAL,FIELD_CONTINUATION,PROFILE_PATCH,PROFILE_DEPENDENTS,HTTP', 'home,stocks,sectors,focus,market,diagnostics'),
    'src/workbench_service/stock_views.py': ('Current PG stock/member aggregation', 'MEMBERS,IDENTITY,HTTP', 'stocks,sectors'),
}


def load(path):
    raw = path.read_bytes()
    if path.suffix == '.gz':
        import gzip
        raw = gzip.decompress(raw)
    return json.loads(raw)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic_csv(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=fields); writer.writeheader()
    for row in rows:
        writer.writerow({k: row.get(k) for k in fields})
    fd, name = tempfile.mkstemp(dir=path.parent, prefix=path.name+'.', suffix='.tmp')
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(('\ufeff'+stream.getvalue()).encode('utf-8')); f.flush(); os.fsync(f.fileno())
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def main():
    if OUT.exists() and any(p.name not in {'MATRIX.json', 'MATRIX.csv', 'RESULT.json'} for p in OUT.iterdir()):
        raise ValueError('PRESERVE_EXISTING_PG_MATRIX')
    refs = {name: load(path) for name, path in EVIDENCE.items()}
    exact56 = load(AUDIT/'continuation_20261013/ORIGINAL56_DISPOSITION_R2/MATRIX.json')
    source_by_path = {r['path']: r for r in exact56 if r['disposition'] == 'ACTIVE_REACHABLE'}
    if set(source_by_path) != set(SOURCE_MAP):
        raise ValueError('EXACT56_ACTIVE_MAPPING_NOT_EXHAUSTIVE')
    http = refs['HTTP']; trace = refs['HTTP_TRACE']
    candidate_ref = http['candidate']; candidate_path = ROOT/candidate_ref['path']
    if sha(candidate_path) != CANDIDATE_SHA or candidate_ref['sha256'] != CANDIDATE_SHA or candidate_path.stat().st_size != candidate_ref['bytes']:
        raise ValueError('CURRENT_CANDIDATE_IDENTITY_MISMATCH')
    candidate = load(candidate_path)
    old_ref = refs['FIELD_ORIGINAL']['candidate']; old_candidate = load(ROOT/old_ref['path'])
    if old_ref['sha256'] != OLD_CANDIDATE_SHA:
        raise ValueError('FIELD_ORACLE_CANDIDATE_IDENTITY_MISMATCH')
    day = candidate['accepted_trade_date']; old_day = old_candidate['accepted_trade_date']
    if day != old_day or day != '2026-10-12': raise ValueError('T0_MISMATCH')
    domain_keys = sorted(set(candidate['owners'][day]) | set(old_candidate['owners'][old_day]))
    owner_conservation = []
    for domain in domain_keys:
        new = candidate['owners'][day].get(domain); old = old_candidate['owners'][old_day].get(domain)
        if not isinstance(new, dict) or not isinstance(old, dict) or new.get('sha256') != old.get('sha256') or new.get('path') != old.get('path'):
            raise ValueError('OWNER_PAYLOAD_NOT_CONSERVED:'+domain)
        owner_conservation.append(dict(domain=domain,path=new['path'],sha256=new['sha256']))
    # The final sealed candidate embeds the exact PG patch authorities whose
    # changed fields and dependent rows were independently checked earlier.
    for key, receipt_name in (('native_profile_semantic_corrections','PROFILE_PATCH'),
                              ('native_profile_dependent_corrections','PROFILE_DEPENDENTS')):
        prepared = refs[receipt_name].get('candidate')
        # Read each intermediate candidate by its immutable reference; it must
        # bind the same correction authority as this final sealed candidate.
        prepared_doc = load(ROOT/prepared['path'])
        if candidate.get(key, {}).get('sha256') != prepared_doc.get(key, {}).get('sha256'):
            raise ValueError('CORRECTION_AUTHORITY_MISMATCH:'+key)
    # Ensure every changed-field check and prior field failure is conserved.
    field_orig = refs['FIELD_ORIGINAL']; coverage = refs['FIELD_COVERAGE']; field_next = refs['FIELD_CONTINUATION']
    if field_orig['total_checks'] != 4526104 or field_orig['error_count'] != 10448:
        raise ValueError('FIELD_ORIGINAL_DENOMINATOR_DRIFT')
    if coverage['complete_original_error_count'] != 10448 or coverage['hidden_other_error_count'] != 0:
        raise ValueError('FIELD_FAILURE_COVERAGE_INCOMPLETE')
    if field_next['reused_pass_checks'] != 4515656 or field_next['new_checks'] != 15672 or field_next['acceptance'] != 'PASS_SCOPED':
        raise ValueError('FIELD_CONTINUATION_NOT_CONSERVED')
    # Bind the current R6 run to the same candidate that all formula receipts name.
    candidate_sensitive = ('SECTOR','RELATIVE','LOO','D1_COUNTER','D1_UPSTREAM','D1_DIGEST')
    for name in candidate_sensitive:
        c = refs[name].get('candidate')
        if not c or c.get('sha256') != CANDIDATE_SHA:
            raise ValueError('NUMERIC_RECEIPT_CANDIDATE_MISMATCH:'+name)
    for name, domain in (('CORE_UNCOVERED','core'), ('PROFILE_RULE','profile')):
        receipt = refs[name]
        if receipt['core' if name == 'CORE_UNCOVERED' else 'profile']['sha256'] != candidate['owners'][day][domain]['sha256']:
            raise ValueError('NUMERIC_OWNER_PAYLOAD_MISMATCH:'+name)
    # Current-dated original Core/period/Profile arithmetic is reusable because
    # the final candidate retains identical owner payload bytes. Source math is
    # separately covered by the component source conservation receipt.
    pg = refs['PG_ROLES']; reader = next(x for x in pg['checks'] if x['role']=='v4_closeout_reader_20261012')
    if reader['system_identifier'] != '7688198230782699460' or reader['database'] != 'market_research':
        raise ValueError('FORMAL_PG_IDENTITY_MISMATCH')
    records = http['records']; page_routes = {'/api/v4/home','/api/v4/stocks','/api/v4/sectors','/api/v4/focus','/api/v4/market','/api/v4/diagnostics'}
    by_route = {r['path']: r for r in records}
    if not page_routes.issubset(by_route) or len(records) != 7 or any(r['http'] != 200 or r['T0'] != day or r['token'] != CANDIDATE_SHA for r in records):
        raise ValueError('CURRENT_HTTP_ROUTE_IDENTITY_MISMATCH')
    if by_route['/api/v4/stocks']['total'] != 5224 or by_route['/api/v4/sectors']['total'] != 400 or by_route['/api/v4/focus']['total'] != 3025:
        raise ValueError('CURRENT_HTTP_ROW_COUNT_MISMATCH')
    for record in records:
        response = WORK/'CURRENT_SOURCE_CANDIDATE_HTTP_R6_R1'/(record['response_sha256']+'.json')
        if not response.is_file() or not isinstance(load(response), dict):
            raise ValueError('CURRENT_HTTP_RESPONSE_DIGEST_MISMATCH:'+record['path'])
    http_trace_rows = {r['path']: r for r in trace['rows']}
    rows=[]
    for path, src in source_by_path.items():
        domain, numeric, route = SOURCE_MAP[path]
        observation = http_trace_rows[path]
        daily_calls = [call for call in src['calls'] if not call['trace'].startswith('CURRENT_SOURCE_CANDIDATE_HTTP')]
        daily_function_calls = sum(sum(call['call_counts'].values()) for call in daily_calls)
        rows.append(dict(path=path,source_sha256=src['source_sha256'],role=domain,
            daily_trace_function_calls=daily_function_calls,
            daily_trace_names=','.join(call['trace'] for call in daily_calls),
            candidate_http_handler_call_count=observation['actual_call_count'],
            pg_identity='market_research/system_identifier=7688198230782699460/SELECT-only reader role',
            numeric_receipts=numeric,route_or_consumer=route,
            status='PASS_SCOPED_CANDIDATE_PG_CHAIN' if route!='candidate_only' else 'CANDIDATE_ONLY_OPTIONAL_SIDECAR'))
    if len(rows) != 20: raise ValueError('ACTIVE_EXACT56_ROW_COUNT')
    OUT.mkdir(parents=True, exist_ok=True)
    atomic_json(AUDIT, OUT/'MATRIX.json', rows)
    atomic_csv(OUT/'MATRIX.csv', rows, ['path','source_sha256','role','daily_trace_function_calls','daily_trace_names','candidate_http_handler_call_count','pg_identity','numeric_receipts','route_or_consumer','status'])
    receipt_index=[]
    for name,path in EVIDENCE.items():
        receipt_index.append(dict(name=name,path=str(path),sha256=sha(path)))
    result=dict(contract_id='V4_CURRENT_CANDIDATE_PG_CONSUMER_MATRIX_R1',
        acceptance='PASS_CURRENT_CANDIDATE_PG_CONSUMER_SCOPE', T0=day, candidate=candidate_ref,
        candidate_owner_payloads_conserved=len(owner_conservation), owner_domains=owner_conservation,
        active_exact56_count=len(rows), routes=records, pg_reader_role='v4_closeout_reader_20261012',
        pg_database=reader['database'], pg_system_identifier=reader['system_identifier'],
        field_projection=dict(original_checks=field_orig['total_checks'],original_failures=field_orig['error_count'],
            failure_buckets=coverage, rechecked=field_next['new_checks'], reused_pass=field_next['reused_pass_checks'],
            acceptance='PASS_SCOPED_CONSERVED_OWNER_VALUES_AND_RELATIVE_SOURCE'),
        profile_corrections=dict(semantic_bff_checks=refs['PROFILE_PATCH']['checks'],
            dependent_consumer_checks=refs['PROFILE_DEPENDENTS']['checks'],
            member_rows=refs['MEMBERS']['member_rows'], identity_rows=refs['IDENTITY']['receipt']['rows']),
        focus=refs['FOCUS'], receipt_index=receipt_index,
        limitations=['The current candidate remains publication=false and production_accepted=false; current Snapshot/Joint publication is the next stage.',
                     'Optional research sidecar first-available history remains incomplete and is not admitted as PIT data or a required current product domain.',
                     'Candidate HTTP payload is current-source/formal-PG only; production Windows runtime remains a later cutover gate.'],
        publication=False, production_cutover=False,
        scope='The final 2026-10-12 sealed candidate retains every base Owner path/hash from the prior full field oracle; final added Profile correction authorities exactly match the separately checked PG authorities. New candidate-bound Core/relative/Sector/D1 receipts and current six-route HTTP all reference this final token. This is candidate PG-consumer acceptance, not publication or production cutover.')
    atomic_json(AUDIT, OUT/'RESULT.json', result)
    print(json.dumps(dict(acceptance=result['acceptance'],active=len(rows),owner_domains=len(owner_conservation),routes=len(records),T0=day)))


if __name__ == '__main__':
    main()
