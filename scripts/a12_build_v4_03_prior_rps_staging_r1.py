# A12 candidate-only replay. Algorithm AST preserved; fixed declared input/output boundary substitutions.
"""Materialize the three prior RPS coordinates before current relative factors."""
from collections import defaultdict
import gzip
import hashlib
import json
import os
from pathlib import Path
import duckdb
from src.v4.factors.core import rps_midrank
ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'reports/audits/a12_v4_03_r1/staging/V4_03_PRIOR_RPS_STAGING_R3.json'
RECEIPT = ROOT / 'reports/audits/a12_v4_03_r1/V4_03_PRIOR_RPS_STAGING_RECEIPT_R3.json'
REQUIRED = {'SH_MAIN', 'SZ_MAIN', 'CHINEXT', 'STAR'}
SPECS = ((1, 5, 6), (3, 5, 8), (3, 20, 23))

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), default=str).encode()).hexdigest()

def atomic(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n', encoding='utf-8')
    os.replace(tmp, path)

def validate_artifact(path, receipt_path):
    """Reject mutation before a downstream delta consumes prior scores."""
    receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
    artifact_sha = sha(path)
    if artifact_sha != receipt['artifact_sha256']:
        raise RuntimeError('prior RPS artifact SHA mismatch')
    payload = json.loads(path.read_text(encoding='utf-8'))
    if len(payload['rows']) != receipt['row_count']:
        raise RuntimeError('prior RPS row count mismatch')
    for row in payload['rows']:
        if row['output_digest'] != digest({k: v for k, v in row.items() if k != 'output_digest'}):
            raise RuntimeError('prior RPS row digest mismatch')
    return (payload, artifact_sha)

def main():
    head_path = ROOT / 'data/v4/V4_DEV_BASELINE_HEAD.json'
    head = json.loads(head_path.read_text(encoding='utf-8'))
    bootstrap_path = ROOT / head['bootstrap_manifest']['path']
    if sha(bootstrap_path) != head['bootstrap_manifest']['sha256']:
        raise RuntimeError('bootstrap digest mismatch')
    bootstrap = json.loads(bootstrap_path.read_text(encoding='utf-8'))
    manifest = json.loads((ROOT / bootstrap['parent_artifacts']['v4_02_manifest']['path']).read_text(encoding='utf-8'))
    daily_ref, calendar_ref = (manifest['components']['DAILY_R7'], manifest['components']['CALENDAR'])
    universe_ref = bootstrap['parent_artifacts']['v4_01_universe']
    daily_path, calendar_path, universe_path = (ROOT / daily_ref['path'], ROOT / calendar_ref['path'], ROOT / universe_ref['path'])
    status_path = ROOT / 'data/v4/artifact_store/a12_authority_candidate_r1/V4_02_DATED_TRADING_STATUS_AUTHORITY_R1.jsonl.gz'
    for path, ref in ((daily_path, daily_ref), (calendar_path, calendar_ref), (universe_path, universe_ref)):
        if sha(path) != ref['sha256']:
            raise RuntimeError(f'accepted input digest mismatch: {path.name}')
    calendar = [d for d in json.loads(calendar_path.read_text(encoding='utf-8'))['session_dates'] if d <= head['accepted_data_cutoff']]
    dates = {n: calendar[-1 - n] for n in {0, 1, 3, 6, 8, 23}}
    snapshot_dates = {dates[1], dates[3]}
    snapshots = defaultdict(dict)
    with gzip.open(universe_path, 'rt', encoding='utf-8') as stream:
        for line in stream:
            row = json.loads(line)
            if row['trade_date'] in snapshot_dates and row['board_scope'] in REQUIRED:
                sid = row['security_id']
                if sid in snapshots[row['trade_date']]:
                    raise RuntimeError('duplicate PIT universe member')
                snapshots[row['trade_date']][sid] = row
    if any((not snapshots[day] for day in snapshot_dates)):
        raise RuntimeError('missing PIT universe snapshot')
    snapshot_ids = {day: digest([(sid, r.get('membership_basis'), r.get('source_revision_id'), r.get('eligibility_status')) for sid, r in sorted(snapshots[day].items())]) for day in snapshot_dates}
    target_ids = set().union(*(set(x) for x in snapshots.values()))
    rows = duckdb.connect().execute("select canonical_security_id, trade_date, qfq_close, price_basis, adjustment_source_revision,\n                  adjusted_quality from read_parquet(?) where trade_date between ? and ?\n                  and board_scope in ('SH_MAIN','SZ_MAIN','CHINEXT','STAR')", [daily_path.as_posix(), int(dates[23].replace('-', '')), int(dates[1].replace('-', ''))]).fetchall()
    daily = {}
    for sid, raw_day, close, basis, revision, quality in rows:
        if sid in target_ids:
            day = f'{raw_day // 10000:04d}-{raw_day // 100 % 100:02d}-{raw_day % 100:02d}'
            daily[sid, day] = (close, f'{basis}:{revision}' if basis and revision else None, quality)
    states = {}
    with gzip.open(status_path, 'rt', encoding='utf-8') as stream:
        for line in stream:
            row = json.loads(line)
            if row['security_id'] in target_ids and dates[23] <= row['trade_date'] <= dates[1]:
                states[row['security_id'], row['trade_date']] = row['status']
    source_digest = digest({'dev_baseline': sha(head_path), 'universe': universe_ref['sha256'], 'daily': daily_ref['sha256'], 'calendar': calendar_ref['sha256'], 'trading_status': sha(status_path)})
    result = []
    for offset, horizon, start_offset in SPECS:
        end, start = (dates[offset], dates[start_offset])
        members = sorted(snapshots[end])
        returns, basis_pairs = ({}, set())
        middle = calendar[calendar.index(start) + 1:calendar.index(end)]
        for sid in members:
            left, right = (daily.get((sid, start)), daily.get((sid, end)))
            valid = left is not None and right is not None and (states.get((sid, start)) == 'ACTUAL_TRADED') and (states.get((sid, end)) == 'ACTUAL_TRADED') and (left[2] == right[2] == 'READY') and (left[1] is not None) and (left[1] == right[1]) and (left[0] is not None) and (right[0] is not None) and (float(left[0]) > 0)
            if valid:
                for day in middle:
                    state = states.get((sid, day))
                    if state == 'SUSPENDED':
                        continue
                    bar = daily.get((sid, day))
                    if state != 'ACTUAL_TRADED' or bar is None or bar[2] != 'READY' or (bar[1] != left[1]):
                        valid = False
                        break
            returns[sid] = float(right[0]) / float(left[0]) - 1 if valid else None
            if valid:
                basis_pairs.add((sid, left[1]))
        scores, _ = rps_midrank(returns, members)
        field = f'rps{horizon}'
        row = {'trade_date': end, 'field_id': field, 'contract_id': 'RPS_MIDRANK_V1', 'contract_version': '1.0.0', 'parameter_set_id': 'V4_03_CORE_FACTOR_PARAMETER_SET_V1', 'universe_snapshot_id': snapshot_ids[end], 'member_count': len(members), 'evaluable_count': sum((v is not None for v in returns.values())), 'input_source_digest': source_digest, 'adjustment_basis_identity': digest(sorted(basis_pairs)), 'input_digest': digest([end, field, snapshot_ids[end], sorted(returns.items()), source_digest]), 'scores': sorted(scores.items()), 'evidence_origin': 'V4_03_STAGE_OWNED_HISTORICAL_STAGING'}
        row['output_digest'] = digest(row)
        result.append(row)
    payload = {'contract_id': 'V4_03_PRIOR_RPS_STAGING_R3', 'version': '1.0.0', 'governing_task': 'docs/audits/V4_03_R3_EXTERNAL_BLOCKER_CLOSURE_TASK_20260928.md', 'source_digest': source_digest, 'rows': result}
    atomic(OUTPUT, payload)
    receipt = {'contract_id': 'V4_03_PRIOR_RPS_STAGING_RECEIPT_R3', 'status': 'STAGING_NOT_STAGE_ACCEPTANCE', 'artifact_sha256': sha(OUTPUT), 'row_count': len(result), 'prior_coordinates': [[r['trade_date'], r['field_id']] for r in result], 'source_digest': source_digest, 'row_output_digests': [r['output_digest'] for r in result], 'evidence_origin': 'V4_03_STAGE_OWNED_HISTORICAL_STAGING', 'governing_task': payload['governing_task']}
    atomic(RECEIPT, receipt)
    print(json.dumps({'status': receipt['status'], 'rows': len(result), 'sha256': receipt['artifact_sha256']}))
if __name__ == '__main__':
    main()
