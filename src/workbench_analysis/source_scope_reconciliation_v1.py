"""Append-only new-day scope proof using the original captured bytes only."""
import json
from pathlib import Path
from .r43_owner_replay import checked_pg as checked, gzrows
from .v4_14_replay_io import digest, publish, ref

CONTRACT = 'SAME_DAY_SOURCE_SCOPE_RECONCILIATION_V1'


def reconcile(root, *, capture_binding, candidate, candidate_binding, trade_date):
    root = Path(root)
    capture = json.loads(checked(root, capture_binding).read_bytes())
    if not isinstance(candidate,dict) or candidate.get('contract_id')!='V4_OPERATIONAL_INCREMENTAL_SUCCESSOR_V1':
        raise ValueError('PG_OPERATIONAL_CANDIDATE_REQUIRED_NO_FILE_FALLBACK')
    head = candidate
    if capture['T0'] != trade_date or head['accepted_trade_date'] != trade_date:
        raise ValueError('SCOPE_TARGET_DATE_MISMATCH')
    life_binding = head['owners'][trade_date]['lifecycle']
    from workbench_db.v4_operational_owner_authority_v2 import read_domain
    life = read_domain(root,head,trade_date,'lifecycle',workspace_root=str(root))
    from workbench_db.v4_membership_reference_pg_v1 import context_snapshot,read as read_memberships
    snapshot = context_snapshot(root,head)
    member_rows=read_memberships(root,head,workspace_root=str(root))
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
    identities = life
    expected = {r['security_id'] for r in life if r.get('security_id')}
    if ({r.get('security_id') for r in identities} != expected or
            any(not r.get('source_security_key') or r.get('trade_date') != trade_date for r in identities)):
        gaps.append('SAME_DAY_LIFECYCLE_SOURCE_MAPPING_INCOMPLETE')
    required_codes = {r['source_security_key'].upper() for r in identities if r.get('source_security_key')}
    if not observed_codes or required_codes != observed_codes:
        gaps.append('SAME_DAY_UNIVERSE_SOURCE_BYTES_INCOMPLETE')
    if any(not r.get('security_id') or r['security_id'] not in expected for r in member_rows):
        gaps.append('SAME_DAY_MEMBERSHIP_IDENTITY_INCOMPLETE')
    # A reconstructed receipt cannot prove contemporary availability.
    if any(s['observation_class'] != 'CURRENT_SOURCE_OBSERVED' for s in sources):
        gaps.append('SAME_DAY_SOURCE_CLOCKS_NOT_OBSERVED')
    evidence = dict(contract_id=CONTRACT, T0=trade_date, source_capture=capture_binding,
        candidate_head=candidate_binding, lifecycle=life_binding, membership=snapshot['memberships'],
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
