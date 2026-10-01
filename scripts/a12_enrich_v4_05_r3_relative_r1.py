# A12 candidate-only replay. Algorithm AST preserved; fixed declared input/output boundary substitutions.
"""Complete current cross-section fields while keeping prior-RPS deltas unknown."""
from __future__ import annotations
from collections import Counter
import gzip
from hashlib import sha256
import json
import os
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.v4.factors.core import rps_midrank
OUT = ROOT / 'reports/audits/a12_v4_05_r1/staging/V4_05_R3_FULL_SCOPE_FACTORS.jsonl.gz'
RECEIPT = ROOT / 'reports/audits/a12_v4_05_r1/V4_05_R3_FULL_SCOPE_FACTORS_RECEIPT.json'
TARGET = '2026-09-28'

def sha(path):
    h = sha256()
    with path.open('rb') as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(part)
    return h.hexdigest()

def digest(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), default=str).encode()).hexdigest()

def main():
    pure = json.loads((ROOT / 'reports/audits/a12_v4_05_r1/V4_05_R3_FACTOR_SOURCE_TIME.json').read_text(encoding='utf-8'))
    reference = json.loads((ROOT / 'reports/v4_05/V4_05_R3_MARKET_REFERENCE.json').read_text(encoding='utf-8'))
    rows = [json.loads(line) for line in gzip.open(ROOT / pure['artifact_path'], 'rt', encoding='utf-8')]
    members = sorted((row['security_id'] for row in rows))
    if len(rows) != 5222 or len(set(members)) != 5222:
        raise ValueError('target cross-section mismatch')
    scores = {}
    for horizon in (5, 20):
        returns = {row['security_id']: row['fields'][f'ret{horizon}']['value'] for row in rows if row['fields'][f'ret{horizon}']['quality_state'] == 'OBSERVED'}
        scores[horizon], _ = rps_midrank(returns, members)
    counts = Counter()
    logical = sha256()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT.with_suffix(OUT.suffix + '.tmp')
    with tmp.open('wb') as raw, gzip.GzipFile(fileobj=raw, mode='wb', filename='', mtime=0, compresslevel=6) as zipped:
        for row in rows:
            sid = row['security_id']
            for horizon in (5, 20):
                name = f'rps{horizon}'
                item = row['fields'][name]
                value = scores[horizon][sid]
                item.update({'value': value, 'quality_state': 'OBSERVED' if value is not None else 'UNKNOWN', 'unknown_reason': None if value is not None else 'RETURN_UNKNOWN', 'contract_id': 'RPS_MIDRANK_V1', 'evidence_origin': 'V4_05_R3_CURRENT_FORWARD_CROSS_SECTION', 'input_digest': digest([pure['logical_digest'], horizon, sorted(scores[horizon].items())]), 'output_digest': digest([sid, name, value])})
            for horizon in (1, 3, 5):
                name = f'rel_market_{horizon}'
                item = row['fields'][name]
                ret = row['fields'][f'ret{horizon}']
                market = reference['horizons'][str(horizon)]
                value = ret['value'] - market['reference_return'] if ret['quality_state'] == 'OBSERVED' and market['quality_state'] == 'OBSERVED' else None
                item.update({'value': value, 'quality_state': 'OBSERVED' if value is not None else 'UNKNOWN', 'unknown_reason': None if value is not None else 'RETURN_OR_MARKET_REFERENCE_UNKNOWN', 'contract_id': 'MARKET_RELATIVE_REFERENCE_V1', 'evidence_origin': 'V4_05_R3_CURRENT_FORWARD_MARKET_REFERENCE', 'input_digest': digest([ret['output_digest'], market['output_digest']]), 'output_digest': digest([sid, name, value])})
            for name, item in row['fields'].items():
                counts[f"{name}:{item['quality_state']}"] += 1
            row['evidence_origin'] = 'V4_05_R3_TARGET_DATE_FULL_SCOPE_WITH_BOOTSTRAP_UNKNOWN'
            line = (json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()
            zipped.write(line)
            logical.update(line)
    os.replace(tmp, OUT)
    receipt = {'contract_id': 'V4_05_R3_FULL_SCOPE_FACTOR_REPLAY_V1', 'status': 'DEGRADED_PASS_PRIOR_RPS_BOOTSTRAP_UNKNOWN', 'artifact_path': OUT.relative_to(ROOT).as_posix(), 'artifact_sha256': sha(OUT), 'logical_digest': logical.hexdigest(), 'row_count': len(rows), 'field_quality_count': dict(counts), 'pure_core_sha256': pure['artifact_sha256'], 'market_reference_sha256': sha(ROOT / 'reports/v4_05/V4_05_R3_MARKET_REFERENCE.json'), 'unresolved_prior_rps_fields': ['rps5_delta1', 'rps5_delta3', 'rps20_delta3'], 'max_source_trade_date': 20260928, 'historical_as_recorded_claim': False}
    temp = RECEIPT.with_suffix('.tmp')
    temp.write_bytes((json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode())
    os.replace(temp, RECEIPT)
    print(json.dumps({'rows': len(rows), 'observed_rps5': counts['rps5:OBSERVED'], 'observed_rel_market_1': counts['rel_market_1:OBSERVED']}))
if __name__ == '__main__':
    main()
