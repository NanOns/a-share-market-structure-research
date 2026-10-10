"""Append-only new-day scope proof using the original captured bytes only."""
import json
from pathlib import Path
from .r43_owner_replay import checked, gzrows
from .v4_14_replay_io import digest, publish, ref

CONTRACT = 'SAME_DAY_SOURCE_SCOPE_RECONCILIATION_V1'


def reconcile(root, *, capture_binding, candidate_binding, trade_date):
    root = Path(root)
    capture = json.loads(checked(root, capture_binding).read_bytes())
    head = json.loads(checked(root, candidate_binding).read_bytes())
    if capture['T0'] != trade_date or head['accepted_trade_date'] != trade_date:
        raise ValueError('SCOPE_TARGET_DATE_MISMATCH')
    life_binding = head['owners'][trade_date]['lifecycle']
    life = json.loads(checked(root, life_binding).read_bytes())
    snapshot = json.loads(checked(root, head['membership_snapshot']).read_bytes())
    sources = capture['sources']
    for source in sources:
        checked(root, source['original_bytes'])
    gaps = []
    captured_members = {s['original_bytes']['sha256'] for s in sources if s['name'].startswith('local_members_')}
    if not snapshot['sources'] or not {s['sha256'] for s in snapshot['sources']} <= captured_members:
        gaps.append('SAME_DAY_MEMBERSHIP_ORIGINAL_BYTES_INCOMPLETE')
    frozen = next((s for s in sources if s['name'] == 'daily_freeze'), None)
    observed_codes = set()
    if frozen:
        original = json.loads(checked(root, frozen['original_bytes']).read_bytes())
        if original.get('target_session') != trade_date:
            raise ValueError('FROZEN_SOURCE_TARGET_DATE_MISMATCH')
        observed_codes = {r['code'].upper() for r in original.get('normalized', {}).get('daily', {}).get('rows', [])}
    identities = life.get('source_rows', life.get('rows', []))
    expected = set(life['active_security_ids'])
    if ({r.get('security_id') for r in identities} != expected or
            any(not r.get('source_security_key') or r.get('trade_date') != trade_date for r in identities)):
        gaps.append('SAME_DAY_LIFECYCLE_SOURCE_MAPPING_INCOMPLETE')
    required_codes = {r['source_security_key'].upper() for r in identities if r.get('source_security_key')}
    if not observed_codes or required_codes != observed_codes:
        gaps.append('SAME_DAY_UNIVERSE_SOURCE_BYTES_INCOMPLETE')
    member_rows = gzrows(checked(root, snapshot['memberships'])) if snapshot.get('memberships') else []
    if any(not r.get('security_id') or r['security_id'] not in expected for r in member_rows):
        gaps.append('SAME_DAY_MEMBERSHIP_IDENTITY_INCOMPLETE')
    # A reconstructed receipt cannot prove contemporary availability.
    if any(s['observation_class'] != 'CURRENT_SOURCE_OBSERVED' for s in sources):
        gaps.append('SAME_DAY_SOURCE_CLOCKS_NOT_OBSERVED')
    evidence = dict(contract_id=CONTRACT, T0=trade_date, source_capture=capture_binding,
        candidate_head=candidate_binding, lifecycle=life_binding, membership=head['membership_snapshot'],
        original_source_receipts=sources, original_captured_at=capture['captured_at'],
        preliminary_security_ids=capture['security_ids'], reconciled_security_ids=sorted(expected),
        reconciled_sector_ids=sorted({r['sector_id'] for r in member_rows}),
        added_security_ids=sorted(expected-set(capture['security_ids'])),
        removed_security_ids=sorted(set(capture['security_ids'])-expected),
        status='SOURCE_GAPS' if gaps else 'SAME_DAY_SCOPE_RECONCILED', source_gaps=gaps,
        production=False, PIT_ELIGIBLE=False, formal_consumer_enabled=False)
    slot = digest([CONTRACT, capture_binding, candidate_binding])
    path = f'data/v4/source_scope_reconciliation_v1/{trade_date}/{slot}/receipt.json'
    if (root/path).exists():
        if json.loads((root/path).read_bytes()) != evidence:
            raise ValueError('SCOPE_RECONCILIATION_OVERWRITE_FORBIDDEN')
        return ref(root, path)
    return publish(root, path, evidence)
