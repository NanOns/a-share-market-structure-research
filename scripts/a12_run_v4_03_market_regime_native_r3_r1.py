# A12 candidate-only replay. Algorithm AST preserved; fixed declared input/output boundary substitutions.
"""Materialize V4-03 daily market primitives from frozen PIT membership and facts."""
from collections import defaultdict, deque
import gzip
import hashlib
import io
import json
import math
import os
from statistics import median
from pathlib import Path
import duckdb
from src.v4.factors.native import market_axis_primitives, market_trend_axis
ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'reports/audits/a12_v4_03_r1/staging/V4_03_MARKET_REGIME_NATIVE_CANDIDATE_R3.jsonl.gz'
RECEIPT = ROOT / 'reports/audits/a12_v4_03_r1/V4_03_MARKET_REGIME_NATIVE_RECEIPT_R3.json'
PATH = ROOT / 'reports/audits/a12_v4_03_r1/staging/V4_03_MARKET_REFERENCE_PATH_CANDIDATE_R3.jsonl.gz'
REQUIRED = {'SH_MAIN', 'SZ_MAIN', 'CHINEXT', 'STAR'}

def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), default=str).encode()).hexdigest()

def atomic(path, value):
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    os.replace(tmp, path)

def main():
    head_path = ROOT / 'data/v4/V4_DEV_BASELINE_HEAD.json'
    head = json.loads(head_path.read_text(encoding='utf-8'))
    bootstrap = json.loads((ROOT / head['bootstrap_manifest']['path']).read_text(encoding='utf-8'))
    manifest = json.loads((ROOT / bootstrap['parent_artifacts']['v4_02_manifest']['path']).read_text(encoding='utf-8'))
    daily_ref, calendar_ref, limit_ref = (manifest['components'][key] for key in ('DAILY_R7', 'CALENDAR', 'FROZEN_R3_BASE'))
    universe_ref = bootstrap['parent_artifacts']['v4_01_universe']
    limit_ref = json.loads((ROOT / 'reports/audits/A12_V4_02_FULL_HISTORICAL_REPAIR_AND_DIFF_R1.json').read_text(encoding='utf8'))['artifacts']['price']
    refs = (daily_ref, calendar_ref, limit_ref, universe_ref)
    if any((sha(ROOT / ref['path']) != ref['sha256'] for ref in refs)):
        raise RuntimeError('accepted source digest mismatch')
    path_receipt = json.loads((ROOT / 'reports/audits/a12_v4_03_r1/V4_03_MARKET_REFERENCE_PATH_RECEIPT_R3.json').read_text(encoding='utf-8'))
    if sha(PATH) != path_receipt['output_sha256']:
        raise RuntimeError('market path artifact digest mismatch')
    path_rows = [json.loads(line) for line in gzip.open(PATH, 'rt', encoding='utf-8')]
    sessions = [row['trade_date'] for row in path_rows]
    session_index = {day: i for i, day in enumerate(sessions)}
    prior_session = {sessions[i]: sessions[i - 1] for i in range(1, len(sessions))}
    if sessions[-1] != head['accepted_data_cutoff']:
        raise RuntimeError('market path cutoff mismatch')
    members = defaultdict(set)
    snapshot_parts = defaultdict(list)
    wanted = set(sessions)
    with gzip.open(ROOT / universe_ref['path'], 'rt', encoding='utf-8') as stream:
        for line in stream:
            row = json.loads(line)
            day = row['trade_date']
            if day in wanted and row['board_scope'] in REQUIRED:
                sid = row['security_id']
                if sid in members[day]:
                    raise RuntimeError('duplicate PIT member')
                members[day].add(sid)
                snapshot_parts[day].append((sid, row.get('membership_basis'), row.get('source_revision_id'), row.get('eligibility_status')))
    snapshot_ids = {day: digest(sorted(snapshot_parts[day])) for day in sessions}
    if any((not members[day] for day in sessions)):
        raise RuntimeError('missing PIT market snapshot')
    status_path = ROOT / 'data/v4/artifact_store/a12_authority_candidate_r1/V4_02_DATED_TRADING_STATUS_AUTHORITY_R1.jsonl.gz'
    suspended = defaultdict(set)
    with gzip.open(status_path, 'rt', encoding='utf-8') as stream:
        for line in stream:
            fact = json.loads(line)
            if fact['status'] == 'SUSPENDED' and fact['trade_date'] in session_index:
                suspended[fact['security_id']].add(fact['trade_date'])
    returns = defaultdict(dict)
    ratios = defaultdict(dict)
    basis_pairs = defaultdict(set)
    histories = defaultdict(lambda: deque(maxlen=20))
    last_amount_day = {}
    sql = "select canonical_security_id, trade_date, qfq_close, amount, price_basis,\n                    adjustment_source_revision, adjusted_quality, trading_status\n             from read_parquet(?) where board_scope in ('SH_MAIN','SZ_MAIN','CHINEXT','STAR')\n             order by canonical_security_id, trade_date"
    cursor = duckdb.connect().execute(sql, [(ROOT / daily_ref['path']).as_posix()])
    last = {}
    while (block := cursor.fetchmany(50000)):
        for sid, raw_day, close, amount, basis, revision, quality, status in block:
            day = f'{raw_day // 10000:04d}-{raw_day // 100 % 100:02d}-{raw_day % 100:02d}'
            current = (day, close, f'{basis}:{revision}' if basis and revision else None, quality, status)
            valid_amount = status == 'ACTUAL_TRADED' and quality == 'READY' and (amount is not None) and math.isfinite(float(amount)) and (amount >= 0) and current[2]
            history = histories[sid]
            if valid_amount:
                prior_amount_day = last_amount_day.get(sid)
                if prior_amount_day in session_index and day in session_index:
                    gap = sessions[session_index[prior_amount_day] + 1:session_index[day]]
                    if any((missing not in suspended[sid] for missing in gap)):
                        history.clear()
                elif prior_amount_day is not None:
                    history.clear()
                if history and history[-1][0] != current[2]:
                    history.clear()
                if sid in members.get(day, ()) and len(history) == 20:
                    mean_amount = sum((x[1] for x in history)) / 20
                    if mean_amount > 0:
                        ratios[day][sid] = float(amount) / mean_amount
                history.append((current[2], float(amount)))
                last_amount_day[sid] = day
            elif status != 'SUSPENDED':
                history.clear()
                last_amount_day.pop(sid, None)
            if sid in members.get(day, ()):
                previous = last.get(sid)
                if previous and previous[0] == prior_session.get(day) and (previous[4] == status == 'ACTUAL_TRADED') and (previous[3] == quality == 'READY') and (previous[2] is not None) and (previous[2] == current[2]) and (previous[1] is not None) and (close is not None) and (float(previous[1]) > 0):
                    returns[day][sid] = float(close) / float(previous[1]) - 1
                    basis_pairs[day].add((sid, current[2]))
            last[sid] = current
    limits = defaultdict(dict)
    with gzip.open(ROOT / limit_ref['path'], 'rt', encoding='utf-8') as stream:
        for line in stream:
            row = json.loads(line)
            day, sid = (row['trade_date'], row['security_id'])
            if sid in members.get(day, ()) and row['limit_status'] in {'LIMIT_UP', 'LIMIT_DOWN', 'NOT_LIMIT'}:
                limits[day][sid] = row['limit_status']
    source_digest = digest({'head': sha(head_path), 'daily': daily_ref['sha256'], 'universe': universe_ref['sha256'], 'calendar': calendar_ref['sha256'], 'price_limit': limit_ref['sha256'], 'trading_status': sha(status_path), 'path': sha(PATH)})
    levels = []
    output_rows = []
    calendar_id = f"V4_02_CALENDAR_SHA256:{calendar_ref['sha256']}"
    for index, day in enumerate(sessions):
        lim, count = (limits[day], len(members[day]))
        prior3 = sessions[index - 3] if index >= 3 else None
        breadth_common = members[day] & members[prior3] if prior3 else set()
        breadth_valid = sorted((sid for sid in breadth_common if sid in returns[day] and sid in returns[prior3])) if prior3 else []
        n_breadth = len(breadth_valid)
        breadth_now = sum((returns[day][sid] > 0 for sid in breadth_valid)) / n_breadth if n_breadth else None
        breadth_old = sum((returns[prior3][sid] > 0 for sid in breadth_valid)) / n_breadth if n_breadth else None
        breadth = breadth_now - breadth_old if n_breadth else None
        participation_values = list(ratios[day].values())
        participation = median(participation_values) if participation_values else None
        limit_count = len(lim)
        down = sum((value == 'LIMIT_DOWN' for value in lim.values()))
        limit_coverage = limit_count / count if count else None
        stress = down / limit_count if limit_count else None
        prior1 = sessions[index - 1] if index else None
        stress_common = members[day] & members[prior1] if prior1 else set()
        stress_valid = sorted((sid for sid in stress_common if sid in lim and sid in limits[prior1])) if prior1 else []
        n_stress = len(stress_valid)
        stress_common_now = sum((lim[sid] == 'LIMIT_DOWN' for sid in stress_valid)) / n_stress if n_stress else None
        stress_common_old = sum((limits[prior1][sid] == 'LIMIT_DOWN' for sid in stress_valid)) / n_stress if n_stress else None
        level = path_rows[index]['level']
        levels.append(level)
        ma20 = sum(levels[-20:]) / 20 if len(levels) >= 20 and all((x is not None for x in levels[-20:])) else None
        prior_ma20 = sum(levels[-25:-5]) / 20 if len(levels) >= 25 and all((x is not None for x in levels[-25:-5])) else None
        basis_id = digest(sorted(basis_pairs[day]))
        identity = {'trade_date': day, 'market_calendar_id': calendar_id, 'market_snapshot_id': snapshot_ids[day], 'adjustment_basis_id': basis_id, 'input_source_digest': source_digest}
        axes = market_axis_primitives(breadth=breadth, participation=participation, limit_coverage=limit_coverage, stress_ratio=stress, prior_stress_ratio=stress_common_old, stress_change_current_ratio=stress_common_now, stress_change_current_provided=True, **identity)
        trend = market_trend_axis(index_close=level, index_ma20=ma20, index_ma20_t_minus_5=prior_ma20, **identity)
        raw = {'breadth_common_count': len(breadth_common), 'breadth_evaluable_count': n_breadth, 'breadth_evaluable_set_id': digest(breadth_valid), 'breadth_t': breadth_now, 'breadth_t_minus_3': breadth_old, 'breadth_delta3': breadth, 'participation_evaluable_count': len(participation_values), 'participation_median_amount_ratio20': participation, 'participation_evaluable_set_id': digest(sorted(ratios[day])), 'limit_down_count': down, 'limit_evaluable_count': limit_count, 'limit_coverage': limit_coverage, 'stress_ratio': stress, 'stress_common_count': len(stress_common), 'stress_evaluable_count': n_stress, 'stress_evaluable_set_id': digest(stress_valid), 'stress_same_member_current_ratio': stress_common_now, 'stress_same_member_prior_ratio': stress_common_old, 'index_close': level, 'index_ma20': ma20, 'index_ma20_t_minus_5': prior_ma20, 'universe_count': count, 'breadth_coverage': n_breadth / len(breadth_common) if breadth_common else None, 'amount_coverage': len(participation_values) / count, 'limit_coverage_denominator': count, 'index_source': 'V4_03_MARKET_REFERENCE_PATH_V1'}
        row = {'trade_date': day, 'raw': raw, 'identity': identity, 'evidence_origin': 'V4_03_PIT_STAGING_CANDIDATE', 'parameter_set_id': 'V4_03_CORE_FACTOR_PARAMETER_SET_V1', 'breadth_axis': axes['breadth_axis'], 'participation_axis': axes['participation_axis'], 'stress_level': axes['stress_level'], 'stress_change': axes['stress_change'], 'trend_axis': trend['trend_axis'], 'axis_quality': {**axes['field_quality'], 'trend_axis': {'quality_state': trend['quality_state'], 'unknown_reason': trend['unknown_reason']}}, 'producer_contracts': {'breadth_axis': axes['contract_id'], 'participation_axis': axes['contract_id'], 'stress_level': axes['contract_id'], 'stress_change': axes['contract_id'], 'trend_axis': trend['contract_id']}}
        row['input_digest'] = digest([identity, raw])
        row['output_digest'] = digest(row)
        output_rows.append(row)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUTPUT.with_suffix(OUTPUT.suffix + '.tmp')
    with tmp.open('wb') as raw_stream, gzip.GzipFile(fileobj=raw_stream, mode='wb', filename='', mtime=0, compresslevel=6) as zipped, io.TextIOWrapper(zipped, encoding='utf-8') as stream:
        for row in output_rows:
            stream.write(json.dumps(row, sort_keys=True, ensure_ascii=False, allow_nan=False) + '\n')
    os.replace(tmp, OUTPUT)
    receipt = {'contract_id': 'V4_03_MARKET_REGIME_NATIVE_RECEIPT_R3', 'status': 'CANDIDATE_NOT_STAGE_ACCEPTANCE', 'evidence_origin': 'V4_03_PIT_STAGING_CANDIDATE', 'formula_contract': 'MARKET_REGIME_V1_REV2_SECTION_27', 'rows': len(output_rows), 'first_session': sessions[0], 'last_session': sessions[-1], 'output_sha256': sha(OUTPUT), 'input_source_digest': source_digest, 'source_hashes': {'daily': daily_ref['sha256'], 'universe': universe_ref['sha256'], 'calendar': calendar_ref['sha256'], 'price_limit': limit_ref['sha256'], 'trading_status': sha(status_path), 'path': sha(PATH)}, 'governing_task': 'docs/audits/V4_03_R3_EXTERNAL_BLOCKER_CLOSURE_TASK_20260928.md'}
    atomic(RECEIPT, receipt)
    print(json.dumps({'status': receipt['status'], 'rows': receipt['rows'], 'sha256': receipt['output_sha256']}))
if __name__ == '__main__':
    main()
