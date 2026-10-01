# Candidate-only R2 replay. Exact R1 AST after reversing declared I/O strings.
"""Rebind R3 current factor values to repaired R4 market reference identities."""
from __future__ import annotations
from collections import Counter
from hashlib import sha256
import gzip
import json
import os
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.v4.canonical_governance_hash import CANONICAL_JSON_SHA256_V1, canonical_json_file_sha256
from src.v4.r4_replay_paths import replay_report_path
IN = ROOT / 'reports/audits/a12_v4_05_r2/staging/V4_05_R3_FULL_SCOPE_FACTORS.jsonl.gz'
REFERENCE = replay_report_path(ROOT, 'reports/v4_05/V4_05_R4_1_MARKET_REFERENCE.json')
OUT = replay_report_path(ROOT, 'reports/audits/a12_v4_05_r2/staging/V4_05_R4_FULL_SCOPE_FACTORS.jsonl.gz')
RECEIPT = replay_report_path(ROOT, 'reports/audits/a12_v4_05_r2/V4_05_R4_FULL_SCOPE_FACTORS_RECEIPT.json')

def digest(value: object) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), default=str).encode()).hexdigest()

def sha(path: Path) -> str:
    h = sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()

def main() -> dict:
    reference = json.loads(REFERENCE.read_text(encoding='utf-8'))
    counts = Counter()
    logical = sha256()
    tmp = OUT.with_suffix(OUT.suffix + '.tmp')
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with tmp.open('wb') as raw, gzip.GzipFile(fileobj=raw, mode='wb', filename='', mtime=0, compresslevel=6) as zipped, gzip.open(IN, 'rt', encoding='utf-8') as source:
        for line in source:
            row = json.loads(line)
            if row['coordinate_basis'] != 'T0_CURRENT_COORDINATE':
                raise ValueError('mixed coordinate basis in R3 source factor')
            sid = row['security_id']
            for horizon in (1, 3, 5):
                name = f'rel_market_{horizon}'
                field = row['fields'][name]
                ret = row['fields'][f'ret{horizon}']
                ref = reference['horizons'][str(horizon)]
                value = ret['value'] - ref['reference_return'] if ret['quality_state'] == 'OBSERVED' and ref['quality_state'] == 'OBSERVED' else None
                field.update({'value': value, 'quality_state': 'OBSERVED' if value is not None else 'UNKNOWN', 'unknown_reason': None if value is not None else 'RETURN_OR_MARKET_REFERENCE_UNKNOWN', 'contract_id': 'MARKET_RELATIVE_REFERENCE_V1', 'contract_version': '1.0.0', 'input_digest': digest([ret['output_digest'], ref['output_digest']]), 'output_digest': digest([sid, name, value]), 'start_universe_snapshot_id': ref['start_universe_snapshot_id'], 'adjustment_basis_id': ref['adjustment_basis_id'], 'window_identity': ref['window_identity'], 'universe_count': ref['universe_count'], 'evaluable_count': ref['evaluable_count'], 'missing_count': ref['missing_count'], 'coverage': ref['coverage']})
            row['evidence_origin'] = 'V4_05_R4_REPAIRED_MARKET_REFERENCE_IDENTITY'
            for name, field in row['fields'].items():
                counts[f"{name}:{field['quality_state']}"] += 1
            payload = (json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()
            zipped.write(payload)
            logical.update(payload)
            counts['rows'] += 1
    os.replace(tmp, OUT)
    receipt = {'contract_id': 'V4_05_R4_FULL_SCOPE_FACTOR_REPLAY_V1', 'status': 'DEGRADED_PASS_PRIOR_RPS_BOOTSTRAP_UNKNOWN', 'artifact_path': OUT.relative_to(ROOT).as_posix(), 'artifact_sha256': sha(OUT), 'logical_digest': logical.hexdigest(), 'row_count': counts.pop('rows'), 'field_quality_count': dict(counts), 'source_r3_sha256': sha(IN), 'market_reference_sha256': canonical_json_file_sha256(REFERENCE), 'market_reference_hash_algorithm': CANONICAL_JSON_SHA256_V1, 'unresolved_prior_rps_fields': ['rps5_delta1', 'rps5_delta3', 'rps20_delta3'], 'formulas_changed': False, 'max_source_trade_date': 20260928, 'historical_as_recorded_claim': False}
    temp = RECEIPT.with_suffix(RECEIPT.suffix + '.tmp')
    temp.write_bytes((json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode('utf-8'))
    os.replace(temp, RECEIPT)
    return receipt
if __name__ == '__main__':
    print(json.dumps(main(), ensure_ascii=False, sort_keys=True))
