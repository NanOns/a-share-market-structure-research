"""Build one PG-only research snapshot with corrected Structure Owner detail."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]

from workbench_db.dm01_data_accepted_head_pg_r1 import read_current as read_data_head
from workbench_db.v4_historical_source_ingress_pg_r1 import admit_bound
from workbench_service.production_v4 import build_snapshot

DAILY_AUTHORITIES = {
    'market': 'v4_market_operational_authority_v1.json',
    'sector': 'v4_sector_operational_authority_v1.json',
    'stocks': 'v4_stock_operational_authority_v1.json',
    'focus': 'v4_focus_operational_authority_v1.json',
    'market_center': 'v4_market_center_authority_v1.json',
    'forward': 'v4_forward_operational_authority_v1.json',
    'replay': 'v4_replay_compare_authority_v1.json',
}


def prepare(runtime_manifest_path):
    source_path = Path(runtime_manifest_path).resolve()
    if not source_path.is_relative_to(ROOT) or not source_path.is_file():
        raise ValueError('STRUCTURE_RUNTIME_MANIFEST_MUST_BE_IN_WORKSPACE')
    rel = source_path.relative_to(ROOT).as_posix()
    raw = source_path.read_bytes()
    binding = dict(path=rel, sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))
    admitted = admit_bound(ROOT, binding)
    if admitted['raw'] != raw:
        raise ValueError('STRUCTURE_RUNTIME_MANIFEST_PG_READBACK_MISMATCH')
    manifest = json.loads(admitted['raw'])
    head = read_data_head(ROOT)
    candidate_head = head['candidate']
    day = manifest.get('owner_inputs', {}).get('trade_date')
    if day != candidate_head.get('accepted_trade_date'):
        raise ValueError('STRUCTURE_OWNER_T0_DOES_NOT_MATCH_CURRENT_DATA_HEAD')
    authority = dict(
        contract_id='V4_STOCK_STRUCTURE_TIMELINE_CANDIDATE_R1',
        contract_version='1.0.0',
        trade_date=day,
        input_data_head=dict(sha256=head['head_sha256']),
        runtime_manifest=binding,
        knowledge_lineage='RECONSTRUCTED_CORRECTED',
        AS_RECORDED=False,
        PIT_ELIGIBLE=False,
    )
    overrides = {'stock_structure_timeline': authority}
    for key, filename in DAILY_AUTHORITIES.items():
        candidate_path = ROOT / 'data/v4/r2_daily_candidates/20261018_r6' / filename
        candidate_raw = candidate_path.read_bytes()
        candidate_ref = dict(path=candidate_path.relative_to(ROOT).as_posix(),
                             sha256=hashlib.sha256(candidate_raw).hexdigest(), bytes=len(candidate_raw))
        candidate_source = admit_bound(ROOT, candidate_ref)
        if candidate_source['raw'] != candidate_raw:
            raise ValueError('DAILY_OWNER_AUTHORITY_PG_READBACK_MISMATCH:' + key)
        owner = json.loads(candidate_source['raw'])
        if owner.get('trade_date') != day or owner.get('input_data_head', {}).get('sha256') != head['head_sha256']:
            raise ValueError('DAILY_OWNER_AUTHORITY_CONTEXT_MISMATCH:' + key)
        overrides[key] = owner
    result = build_snapshot(ROOT, authority_overrides=overrides)
    descriptor = result['pointer']
    print(json.dumps(dict(
        contract_id='V4_STOCK_STRUCTURE_TIMELINE_PG_CANDIDATE_BUILD_R1',
        result=result['status'],
        trade_date=day,
        input_data_head_sha256=head['head_sha256'],
        snapshot_schema=descriptor['schema'],
        logical_digest=descriptor['logical_digest'],
        counts=result['counts'],
        accepted_head_changed=False,
        joint_authority_changed=False,
        production_cutover=False,
    ), ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--runtime-manifest', required=True)
    args = parser.parse_args()
    prepare(args.runtime_manifest)


if __name__ == '__main__':
    main()
