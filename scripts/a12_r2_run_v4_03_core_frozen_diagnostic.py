# Candidate-only R2 replay. Exact R1 AST after reversing declared I/O strings.
"""Required-board cutoff diagnostic for implemented CORE_FACTOR_V1 fields.

This is deliberately not an accepted full V4-03 run: RPS, market reference,
machine algorithm contracts, and full independent postcheck remain separate.
"""
from collections import Counter, defaultdict
import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import threading
import time
import duckdb
import psutil
from src.v4.factors import Bar, Observation, compute_core
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'reports/audits/a12_v4_03_r2/staging/V4_03_CORE_REQUIRED_SCOPE_DIAGNOSTIC_R1.jsonl.gz'
RECEIPT = ROOT / 'reports/audits/a12_v4_03_r2/V4_03_CORE_REQUIRED_SCOPE_DIAGNOSTIC_RECEIPT_R1.json'
REQUIRED = {'SH_MAIN', 'SZ_MAIN', 'CHINEXT', 'STAR'}

def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(part)
    return h.hexdigest()

def atomic_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_bytes((json.dumps(obj, sort_keys=True, indent=2, ensure_ascii=False) + '\n').encode('utf-8'))
    os.replace(temp, path)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--full-history', action='store_true', help='use every accepted session through frozen cutoff and write R2 candidate')
    args = parser.parse_args()
    out_path = ROOT / 'reports/audits/a12_v4_03_r2/staging/V4_03_CORE_FULL_HISTORY_CANDIDATE_R2.jsonl.gz' if args.full_history else OUT
    receipt_path = ROOT / 'reports/audits/a12_v4_03_r2/V4_03_CORE_FULL_HISTORY_CANDIDATE_RECEIPT_R2.json' if args.full_history else RECEIPT
    start = time.monotonic()
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
    sampler = threading.Thread(target=sample_memory, name='v4-03-core-memory-sampler', daemon=True)
    sampler.start()
    head_path = ROOT / 'data/v4/V4_DEV_BASELINE_HEAD.json'
    head = json.loads(head_path.read_text(encoding='utf-8'))
    if head['accepted_data_cutoff'] != '2026-09-24':
        raise RuntimeError('DEV baseline cutoff drift')
    bootstrap_path = ROOT / head['bootstrap_manifest']['path']
    if sha(bootstrap_path) != head['bootstrap_manifest']['sha256']:
        raise RuntimeError('DEV baseline bootstrap manifest drift')
    bootstrap = json.loads(bootstrap_path.read_text(encoding='utf-8'))
    manifest = json.loads((ROOT / bootstrap['parent_artifacts']['v4_02_manifest']['path']).read_text(encoding='utf-8'))
    daily_ref = manifest['components']['DAILY_R7']
    daily_path = ROOT / daily_ref['path']
    if sha(daily_path) != daily_ref['sha256']:
        raise RuntimeError('accepted adjusted daily digest drift')
    calendar_ref = manifest['components']['CALENDAR']
    calendar_path = ROOT / calendar_ref['path']
    if sha(calendar_path) != calendar_ref['sha256']:
        raise RuntimeError('accepted calendar digest drift')
    calendar = [x for x in json.loads(calendar_path.read_text(encoding='utf-8'))['session_dates'] if x <= head['accepted_data_cutoff']]
    sessions = calendar if args.full_history else calendar[-200:]
    first_session = sessions[0]
    cutoff = head['accepted_data_cutoff']
    universe_ref = bootstrap['parent_artifacts']['v4_01_universe']
    universe_path = ROOT / universe_ref['path']
    if sha(universe_path) != universe_ref['sha256']:
        raise RuntimeError('historical universe digest drift')
    members = {}
    with gzip.open(universe_path, 'rt', encoding='utf-8') as stream:
        for line in stream:
            row = json.loads(line)
            if row['trade_date'] == cutoff and row['board_scope'] in REQUIRED:
                sid = row['security_id']
                if sid in members:
                    raise RuntimeError(f'duplicate PIT universe member {sid}')
                members[sid] = row
    if not members:
        raise RuntimeError('no required-scope historical universe at cutoff')
    first_int = int(first_session.replace('-', ''))
    connection = duckdb.connect()
    sql = 'select canonical_security_id, trade_date, qfq_open, qfq_high, qfq_low,\n                    qfq_close, amount, volume, price_basis, adjustment_source_revision,\n                    adjusted_quality, trading_status\n             from read_parquet(?) where trade_date between ? and ?\n             order by canonical_security_id, trade_date'
    cursor = connection.execute(sql, [daily_path.as_posix(), first_int, int(cutoff.replace('-', ''))])
    actual = defaultdict(dict)
    rejected = defaultdict(dict)
    raw_rows = 0
    while (block := cursor.fetchmany(25000)):
        for row in block:
            sid, day, op, hi, lo, cl, amount, volume, basis, revision, quality, status = row
            if sid not in members:
                continue
            raw_rows += 1
            date = f'{day // 10000:04d}-{day // 100 % 100:02d}-{day % 100:02d}'
            if quality == 'READY' and status == 'ACTUAL_TRADED' and all((x is not None for x in (op, hi, lo, cl, amount, volume, basis, revision))):
                actual[sid][date] = Bar(float(op), float(hi), float(lo), float(cl), float(amount), float(volume), f'{basis}:{revision}', daily_ref['sha256'])
            else:
                rejected[sid][date] = 'ADJUSTMENT_UNKNOWN' if quality != 'READY' else 'UNKNOWN'
    status_path = ROOT / 'data/v4/artifact_store/a12_authority_candidate_r2/V4_02_DATED_TRADING_STATUS_AUTHORITY_R2.jsonl.gz'
    suspended = defaultdict(set)
    with gzip.open(status_path, 'rt', encoding='utf-8') as stream:
        for line in stream:
            row = json.loads(line)
            if row['trade_date'] >= first_session and row['security_id'] in members and (row['status'] == 'SUSPENDED'):
                suspended[row['security_id']].add(row['trade_date'])
    counts = Counter()
    unknown = Counter()
    board_counts = Counter()
    board_observed = Counter()
    temp = out_path.with_suffix(out_path.suffix + '.tmp')
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with temp.open('wb') as raw_stream, gzip.GzipFile(fileobj=raw_stream, mode='wb', filename='', mtime=0, compresslevel=6) as compressed, io.TextIOWrapper(compressed, encoding='utf-8') as stream:
        for sid, member in sorted(members.items()):
            observations = []
            seen = False
            for day in sessions:
                bar = actual[sid].get(day)
                state = rejected[sid].get(day)
                if bar is not None or state is not None or day in suspended[sid]:
                    seen = True
                if bar is not None:
                    observations.append(Observation(day, 'ACTUAL', bar))
                elif state is not None:
                    observations.append(Observation(day, state))
                elif day in suspended[sid]:
                    observations.append(Observation(day, 'CONFIRMED_SUSPENSION'))
                else:
                    observations.append(Observation(day, 'UNKNOWN' if seen else 'PRE_LISTING'))
            fields = compute_core(observations, sid)
            board = member['board_scope']
            board_counts[board] += 1
            for name, result in fields.items():
                counts[name, result.quality_state] += 1
                board_observed[board, name] += result.quality_state == 'OBSERVED'
                if result.unknown_reason:
                    unknown[name, result.unknown_reason] += 1
            stream.write(json.dumps({'security_id': sid, 'trade_date': cutoff, 'board_scope': board, 'evidence_origin': 'DIAGNOSTIC_NON_PIT', 'fields': {k: asdict(v) for k, v in sorted(fields.items())}}, ensure_ascii=False, sort_keys=True, allow_nan=False) + '\n')
    os.replace(temp, out_path)
    elapsed = time.monotonic() - start
    sample_stop.set()
    sampler.join(timeout=1)
    cpu_ended = process.cpu_times()
    cpu_seconds = cpu_ended.user + cpu_ended.system - (cpu_started.user + cpu_started.system)
    memory = process.memory_info()
    logical_cpus = os.cpu_count() or 1
    measurement = {'factor_compute_time_seconds': round(elapsed, 3), 'stage_wall_time_seconds': round(elapsed, 3), 'process_cpu_seconds': round(cpu_seconds, 3), 'process_cpu_percent_of_one_logical_cpu': round(cpu_seconds / elapsed * 100, 2) if elapsed else 0, 'process_cpu_percent_of_host_capacity': round(cpu_seconds / elapsed / logical_cpus * 100, 2) if elapsed else 0, 'sampled_peak_rss_bytes': peak_rss[0], 'os_peak_working_set_bytes': getattr(memory, 'peak_wset', None), 'hardware': {'platform': platform.platform(), 'processor': platform.processor(), 'logical_cpu_count': logical_cpus}, 'cache_state': 'OS_AND_DUCKDB_CACHE_NOT_CONTROLLED_OR_CLEARED', 'dataset_identity': sha(head_path)}
    receipt = {'contract_id': 'V4_03_CORE_FULL_HISTORY_CANDIDATE_RECEIPT_R2' if args.full_history else 'V4_03_CORE_REQUIRED_SCOPE_DIAGNOSTIC_R1', 'status': 'FULL_INPUT_HISTORY_CUTOFF_CANDIDATE_NOT_STAGE_ACCEPTANCE' if args.full_history else 'DIAGNOSTIC_ONLY_NOT_STAGE_ACCEPTANCE', 'cutoff': cutoff, 'dev_baseline_head_sha256': sha(head_path), 'universe_sha256': universe_ref['sha256'], 'daily_sha256': daily_ref['sha256'], 'calendar_sha256': calendar_ref['sha256'], 'trading_status_sha256': sha(status_path), 'output_sha256': sha(out_path), 'rows_in': raw_rows, 'rows_out': len(members), 'security_count': len(members), 'board_count': dict(sorted(board_counts.items())), 'field_quality_count': {f'{k[0]}:{k[1]}': v for k, v in sorted(counts.items())}, 'field_unknown_reasons': {f'{k[0]}:{k[1]}': v for k, v in sorted(unknown.items())}, 'board_observed_count': {f'{k[0]}:{k[1]}': v for k, v in sorted(board_observed.items())}, 'elapsed_seconds': round(elapsed, 3), 'performance_measurement': measurement, 'history_window_sessions': len(sessions), 'history_start_session': first_session, 'limitations': ['CORE_FACTOR_V1 stock fields only', 'cutoff only; historical daily first-availability replay pending', 'no RPS or market reference', 'no accepted publication'] if args.full_history else ['CORE_FACTOR_V1 stock fields only', '200-session bounded diagnostic history', 'no RPS or market reference', 'no independent full-market postcheck', 'no accepted publication']}
    atomic_json(receipt_path, receipt)
    print(json.dumps({'status': receipt['status'], 'rows_out': receipt['rows_out'], 'elapsed_seconds': receipt['elapsed_seconds']}))
if __name__ == '__main__':
    main()
