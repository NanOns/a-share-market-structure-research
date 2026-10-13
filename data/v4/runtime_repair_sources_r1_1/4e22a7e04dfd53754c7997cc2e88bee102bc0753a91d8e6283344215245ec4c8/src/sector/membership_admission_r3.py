"""R3 basis, knowledge-time and dated active-universe admission gates."""
from datetime import date
from zoneinfo import ZoneInfo
from typing import Any, Mapping
from sector.membership_baseline import FORMAL_REQUIRED_BOARDS, formal_membership_eligible, parse_timestamp

QUALITY_BASIS = {
    'PIT_OBSERVED_ACCEPTED': 'PIT_OBSERVED',
    'CURRENT_TDX_DIAGNOSTIC': 'CURRENT_TDX_MEMBERSHIP',
    'CURRENT_REPLAY_DIAGNOSTIC': 'CURRENT_MEMBERSHIP_REPLAY',
    'DERIVED_PARENT_DIAGNOSTIC': 'DERIVED_PARENT_MEMBERSHIP',
}

def basis_quality_compatible(basis: str, quality: str) -> bool:
    return quality not in QUALITY_BASIS or QUALITY_BASIS[quality] == basis

def basis_chain_valid(revision: Mapping[str, Any], snapshot: Mapping[str, Any], fact: Mapping[str, Any]) -> bool:
    return (revision.get('membership_basis') == snapshot.get('membership_basis') == fact.get('membership_basis')
            and all(basis_quality_compatible(x.get('membership_basis'), x.get(q))
                    for x, q in [(revision,'revision_quality'),(snapshot,'membership_quality'),(fact,'membership_quality')]))

def active_identity_reason(identity: Mapping[str, Any] | None, target: str, cutoff: str) -> str | None:
    if not identity or not identity.get('security_id'):
        return 'UNMAPPED_IDENTITY'
    if identity.get('security_type') != 'A_STOCK':
        return 'NON_EQUITY'
    # Accepted R7 uses MAIN plus an explicit exchange; normalize that contract,
    # without inferring lifecycle or board from code patterns.
    board = identity.get('board')
    if board == 'MAIN':
        board = {'SH':'SH_MAIN','SZ':'SZ_MAIN'}.get(identity.get('exchange'))
    if board not in FORMAL_REQUIRED_BOARDS:
        return 'OPTIONAL_BOARD_OUTSIDE_REQUIRED_SCOPE'
    if not identity.get('list_date'):
        return 'UNVERIFIED_LISTING_DATE'
    if date.fromisoformat(identity['list_date']) > date.fromisoformat(target):
        return 'NOT_LISTED_AT_TARGET'
    if identity.get('delist_date') and identity['delist_date'] <= target:
        return 'DELISTED_AT_TARGET'
    if identity.get('system_available_at') and parse_timestamp(identity['system_available_at']) > parse_timestamp(cutoff):
        return 'IDENTITY_UNAVAILABLE_AT_CUTOFF'
    return None

def formal_membership_eligible_r3(row: Mapping[str, Any], identity: Mapping[str, Any] | None) -> bool:
    try:
        observation_day = parse_timestamp(row.get('observed_at')).astimezone(ZoneInfo('Asia/Shanghai')).date().isoformat()
    except (TypeError, ValueError):
        return False
    return (formal_membership_eligible(row)
            and row.get('source_revision_membership_basis') == row.get('snapshot_membership_basis') == row.get('membership_basis') == 'PIT_OBSERVED'
            and row.get('target_trade_date') == observation_day
            and identity is not None and identity.get('security_id') == row.get('security_id')
            and identity.get('acceptance') == 'ACCEPTED'
            and active_identity_reason(identity, row['target_trade_date'], row['cutoff']) is None)
