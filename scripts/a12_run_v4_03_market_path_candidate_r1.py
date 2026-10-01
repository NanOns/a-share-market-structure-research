# A12 candidate-only replay. Algorithm AST preserved; fixed declared input/output boundary substitutions.
"""Build a frozen-baseline daily-rebalanced research-market path candidate."""
from collections import defaultdict
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import platform
import threading
import time
import duckdb
import psutil
from src.v4.factors.native import historical_market_path
ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'reports/audits/a12_v4_03_r1/staging/V4_03_MARKET_REFERENCE_PATH_CANDIDATE_R1.jsonl.gz'
RECEIPT = ROOT / 'reports/audits/a12_v4_03_r1/V4_03_MARKET_PATH_CANDIDATE_RECEIPT_R1.json'
REQUIRED = {'SH_MAIN', 'SZ_MAIN', 'CHINEXT', 'STAR'}

def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(part)
    return h.hexdigest()

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), default=str).encode()).hexdigest()

def write_atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    os.replace(tmp, path)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--full-history', action='store_true')
    args = parser.parse_args()
    output_path = ROOT / ('reports/audits/a12_v4_03_r1/staging/V4_03_MARKET_REFERENCE_PATH_CANDIDATE_R3.jsonl.gz' if args.full_history else 'reports/audits/a12_v4_03_r1/staging/V4_03_MARKET_REFERENCE_PATH_CANDIDATE_R1.jsonl.gz')
    receipt_path = ROOT / ('reports/audits/a12_v4_03_r1/V4_03_MARKET_REFERENCE_PATH_RECEIPT_R3.json' if args.full_history else 'reports/audits/a12_v4_03_r1/V4_03_MARKET_PATH_CANDIDATE_RECEIPT_R1.json')
    started = time.monotonic()
    process = psutil.Process()
    cpu_started = process.cpu_times()
    peak_rss = [process.memory_info().rss]
    sample_stop = threading.Event()

    def sample_memory():
        while not sample_stop.wait(0.05):
            try:
                peak_rss[0] = max(peak_rss[0], process.memory_info().rss)
            except psutil.Error:
                return
    sampler = threading.Thread(target=sample_memory, name='v4-03-market-path-memory-sampler', daemon=True)
    sampler.start()
    head_path = ROOT / 'data/v4/V4_DEV_BASELINE_HEAD.json'
    head = json.loads(head_path.read_text(encoding='utf-8'))
    if head.get('accepted_data_cutoff') != '2026-09-24':
        raise RuntimeError('frozen V4_DEV_BASELINE cutoff changed')
    bootstrap_path = ROOT / head['bootstrap_manifest']['path']
    if sha(bootstrap_path) != head['bootstrap_manifest']['sha256']:
        raise RuntimeError('DEV baseline manifest digest mismatch')
    bootstrap = json.loads(bootstrap_path.read_text(encoding='utf-8'))
    manifest = json.loads((ROOT / bootstrap['parent_artifacts']['v4_02_manifest']['path']).read_text(encoding='utf-8'))
    daily_ref = manifest['components']['DAILY_R7']
    calendar_ref = manifest['components']['CALENDAR']
    universe_ref = bootstrap['parent_artifacts']['v4_01_universe']
    daily_path, calendar_path, universe_path = (ROOT / daily_ref['path'], ROOT / calendar_ref['path'], ROOT / universe_ref['path'])
    for path, ref in ((daily_path, daily_ref), (calendar_path, calendar_ref), (universe_path, universe_ref)):
        if sha(path) != ref['sha256']:
            raise RuntimeError(f'accepted source digest mismatch: {path.name}')
    calendar = [d for d in json.loads(calendar_path.read_text(encoding='utf-8'))['session_dates'] if d <= head['accepted_data_cutoff']]
    if not args.full_history:
        calendar = calendar[-200:]
    wanted = set(calendar)
    snapshots = defaultdict(dict)
    with gzip.open(universe_path, 'rt', encoding='utf-8') as stream:
        for line in stream:
            row = json.loads(line)
            if row['trade_date'] in wanted and row['board_scope'] in REQUIRED:
                sid = row['security_id']
                if sid in snapshots[row['trade_date']]:
                    raise RuntimeError(f"duplicate PIT membership: {row['trade_date']} {sid}")
                snapshots[row['trade_date']][sid] = row
    missing_snapshots = [day for day in calendar if not snapshots[day]]
    if missing_snapshots:
        raise RuntimeError(f'accepted PIT required-scope snapshot missing: {missing_snapshots[0]}')
    snapshot_ids = {day: digest([(sid, row.get('membership_basis'), row.get('source_revision_id'), row.get('eligibility_status')) for sid, row in sorted(snapshots[day].items())]) for day in calendar}
    target_ids = set().union(*(set(snapshots[day]) for day in calendar))
    daily: dict[tuple[str, str], dict] = {}
    start_int = int(calendar[0].replace('-', ''))
    end_int = int(calendar[-1].replace('-', ''))
    connection = duckdb.connect()
    query = "select canonical_security_id, trade_date, qfq_close, price_basis,\n                      adjustment_source_revision, adjusted_quality, trading_status, board_scope\n               from read_parquet(?) where trade_date between ? and ?\n                 and board_scope in ('SH_MAIN','SZ_MAIN','CHINEXT','STAR')"
    cursor = connection.execute(query, [daily_path.as_posix(), start_int, end_int])
    rows_in = 0
    while (block := cursor.fetchmany(50000)):
        for sid, raw_day, close, basis, revision, quality, trading_status, _board in block:
            if sid not in target_ids:
                continue
            rows_in += 1
            day = f'{raw_day // 10000:04d}-{raw_day // 100 % 100:02d}-{raw_day % 100:02d}'
            daily[sid, day] = {'close': close, 'basis': f'{basis}:{revision}' if basis and revision else None, 'quality': quality, 'status': trading_status}
    status_path = ROOT / 'data/v4/artifact_store/a12_authority_candidate_r1/V4_02_DATED_TRADING_STATUS_AUTHORITY_R1.jsonl.gz'
    if not status_path.exists():
        raise RuntimeError('accepted dated trading-status input missing')
    statuses = defaultdict(dict)
    with gzip.open(status_path, 'rt', encoding='utf-8') as stream:
        for line in stream:
            row = json.loads(line)
            if row['security_id'] in target_ids and calendar[0] <= row['trade_date'] <= calendar[-1]:
                statuses[row['security_id']][row['trade_date']] = row['status']
    parameters = json.loads((ROOT / 'config/v4_03_parameter_registry_v1.json').read_text(encoding='utf-8'))
    max_missing = next((row['value'] for row in parameters['entries'] if row['parameter_id'] == 'V4_03_MARKET_REFERENCE_MAX_MISSING_FRACTION'))
    if max_missing is None:
        raise RuntimeError('market-reference missing threshold is unbound')
    daily_returns = []
    daily_identities = []
    for index in range(1, len(calendar)):
        start, end = (calendar[index - 1], calendar[index])
        members = sorted(snapshots[start])
        returns, used_basis = ({}, set())
        for sid in members:
            left, right = (daily.get((sid, start)), daily.get((sid, end)))
            if left is None or right is None or statuses[sid].get(start) != 'ACTUAL_TRADED' or (statuses[sid].get(end) != 'ACTUAL_TRADED') or (left['quality'] != 'READY') or (right['quality'] != 'READY') or (left['basis'] is None) or (left['basis'] != right['basis']) or (left['close'] is None) or (right['close'] is None) or (left['close'] <= 0):
                returns[sid] = None
            else:
                returns[sid] = float(right['close']) / float(left['close']) - 1
                used_basis.add((sid, left['basis']))
        evaluable = {sid: value for sid, value in returns.items() if value is not None}
        missing = len(members) - len(evaluable)
        coverage = len(evaluable) / len(members) if members else None
        reason = 'EMPTY_START_UNIVERSE' if not members else 'MISSING_COVERAGE_EXCEEDED' if missing / len(members) > max_missing else None
        reference = sum(evaluable.values()) / len(evaluable) if evaluable and reason is None else None
        daily_returns.append((end, reference))
        daily_identities.append({'trade_date': end, 'start_session': start, 'end_session': end, 'start_universe_snapshot_id': snapshot_ids[start], 'evaluable_set_identity': digest(sorted(evaluable)), 'universe_count': len(members), 'evaluable_count': len(evaluable), 'missing_count': missing, 'coverage': coverage, 'quality_state': 'UNKNOWN' if reason else 'OBSERVED', 'unknown_reason': reason, 'reference_return': reference, 'adjustment_basis_id': digest(sorted(used_basis)), 'market_calendar_id': f"V4_02_CALENDAR_SHA256:{calendar_ref['sha256']}"})
    source_digest = digest({'dev_baseline': sha(head_path), 'daily': daily_ref['sha256'], 'universe': universe_ref['sha256'], 'calendar': calendar_ref['sha256'], 'trading_status': sha(status_path), 'sessions': calendar})
    path_rows = historical_market_path(daily_returns, start_sessions=[row['start_session'] for row in daily_identities], start_universe_snapshot_ids=[row['start_universe_snapshot_id'] for row in daily_identities], market_calendar_id=f"V4_02_CALENDAR_SHA256:{calendar_ref['sha256']}", input_source_digest=source_digest, series_version='DAILY_REBALANCED_RESEARCH_INDEX_V1')
    temp = output_path.with_suffix(output_path.suffix + '.tmp')
    output_path.parent.mkdir(parents=True, exist_ok=True)
    base_row = {'contract_id': 'V4_03_MARKET_REFERENCE_PATH_V1', 'contract_version': '1.0.0', 'parameter_set_id': parameters['parameter_set_id'], 'evidence_origin': 'V4_03_PIT_STAGING_CANDIDATE' if args.full_history else 'DIAGNOSTIC_NON_PIT', 'trade_date': calendar[0], 'start_session': None, 'end_session': calendar[0], 'start_universe_snapshot_id': snapshot_ids[calendar[0]], 'evaluable_set_identity': None, 'universe_count': len(snapshots[calendar[0]]), 'evaluable_count': None, 'missing_count': None, 'coverage': None, 'quality_state': 'OBSERVED', 'unknown_reason': None, 'reference_return': None, 'level': 1.0, 'path_identity': 'DAILY_REBALANCED_RESEARCH_INDEX', 'series_version': 'DAILY_REBALANCED_RESEARCH_INDEX_V1', 'rebase_policy': 'UNKNOWN_SUFFIX_UNTIL_NEW_SERIES_VERSION', 'adjustment_basis_id': None, 'market_calendar_id': f"V4_02_CALENDAR_SHA256:{calendar_ref['sha256']}", 'input_source_digest': source_digest, 'window_identity': digest([calendar_ref['sha256'], calendar[0], snapshot_ids[calendar[0]], 'SERIES_BASE_1.0'])}
    base_row['input_digest'] = digest([source_digest, calendar[0], snapshot_ids[calendar[0]], 'SERIES_BASE_1.0'])
    base_row['output_digest'] = digest(base_row)
    temp = output_path.with_suffix(output_path.suffix + '.tmp')
    with temp.open('wb') as raw, gzip.GzipFile(fileobj=raw, mode='wb', filename='', mtime=0, compresslevel=6) as zipped:
        zipped.write((json.dumps(base_row, ensure_ascii=False, sort_keys=True, allow_nan=False) + '\n').encode('utf-8'))
        for facts, path_fact in zip(daily_identities, path_rows):
            row = {'contract_id': 'V4_03_MARKET_REFERENCE_PATH_V1', 'contract_version': '1.0.0', 'parameter_set_id': parameters['parameter_set_id'], 'evidence_origin': 'V4_03_PIT_STAGING_CANDIDATE' if args.full_history else 'DIAGNOSTIC_NON_PIT', **facts, 'daily_return_quality_state': facts['quality_state'], 'daily_return_unknown_reason': facts['unknown_reason'], 'quality_state': path_fact['quality_state'], 'unknown_reason': path_fact['unknown_reason'], 'daily_return': path_fact['daily_return'], 'level': path_fact['level'], 'path_identity': path_fact['path_identity'], 'series_version': path_fact['series_version'], 'rebase_policy': path_fact['rebase_policy'], 'input_source_digest': source_digest, 'window_identity': digest([facts['market_calendar_id'], facts['start_session'], facts['end_session'], facts['start_universe_snapshot_id'], facts['adjustment_basis_id']])}
            row['input_digest'] = path_fact['input_digest']
            row['output_digest'] = digest(row)
            zipped.write((json.dumps(row, ensure_ascii=False, sort_keys=True, allow_nan=False) + '\n').encode('utf-8'))
    os.replace(temp, output_path)
    unknown_days = [row['trade_date'] for row, path in zip(daily_identities, path_rows) if path['quality_state'] == 'UNKNOWN']
    elapsed = time.monotonic() - started
    sample_stop.set()
    sampler.join(timeout=1)
    cpu_ended = process.cpu_times()
    cpu_seconds = cpu_ended.user + cpu_ended.system - (cpu_started.user + cpu_started.system)
    memory = process.memory_info()
    logical_cpus = os.cpu_count() or 1
    measurement = {'factor_compute_time_seconds': round(elapsed, 3), 'stage_wall_time_seconds': round(elapsed, 3), 'process_cpu_seconds': round(cpu_seconds, 3), 'process_cpu_percent_of_one_logical_cpu': round(cpu_seconds / elapsed * 100, 2) if elapsed else 0, 'process_cpu_percent_of_host_capacity': round(cpu_seconds / elapsed / logical_cpus * 100, 2) if elapsed else 0, 'sampled_peak_rss_bytes': peak_rss[0], 'os_peak_working_set_bytes': getattr(memory, 'peak_wset', None), 'hardware': {'platform': platform.platform(), 'processor': platform.processor(), 'logical_cpu_count': logical_cpus}, 'cache_state': 'OS_AND_DUCKDB_CACHE_NOT_CONTROLLED_OR_CLEARED', 'dataset_identity': source_digest}
    receipt = {'contract_id': 'V4_03_MARKET_REFERENCE_PATH_RECEIPT_R3' if args.full_history else 'V4_03_MARKET_PATH_CANDIDATE_RECEIPT_R1', 'status': 'CANDIDATE_NOT_STAGE_ACCEPTANCE', 'path_identity': 'DAILY_REBALANCED_RESEARCH_INDEX', 'evidence_origin': 'V4_03_PIT_STAGING_CANDIDATE' if args.full_history else 'DIAGNOSTIC_NON_PIT', 'series_version': 'DAILY_REBALANCED_RESEARCH_INDEX_V1', 'cutoff': calendar[-1], 'sessions': len(calendar), 'daily_returns': len(daily_returns), 'rows_in': rows_in, 'required_scope_member_set_policy': 'PIT_UNIVERSE_AT_START_SESSION', 'unknown_daily_return_count': len(unknown_days), 'first_unknown_daily_return': unknown_days[0] if unknown_days else None, 'rebase_policy': 'UNKNOWN_SUFFIX_UNTIL_NEW_SERIES_VERSION', 'source_digest': source_digest, 'output_sha256': sha(output_path), 'first_session': calendar[0], 'last_session': calendar[-1], 'governing_task': 'docs/audits/V4_03_R3_EXTERNAL_BLOCKER_CLOSURE_TASK_20260928.md' if args.full_history else None, 'elapsed_seconds': round(elapsed, 3), 'performance_measurement': measurement, 'scanner_run_count': 0, 'trading_run_count': 0, 'tdx_root_write_count': 0}
    write_atomic_json(receipt_path, receipt)
    print(json.dumps({'status': receipt['status'], 'sessions': receipt['sessions'], 'daily_returns': receipt['daily_returns'], 'unknown_returns': receipt['unknown_daily_return_count'], 'elapsed_seconds': receipt['elapsed_seconds']}))
if __name__ == '__main__':
    main()
