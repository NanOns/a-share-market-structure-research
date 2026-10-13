"""Research comparison of legacy qualification with Lifecycle, never an A05 grant."""
import re
from .legacy_valid_member_a05_v1 import exact_value

CONTRACT = 'LEGACY_VALID_MEMBER_QUALIFICATION_AUDIT_V3'


def compare(row, *, trade_date, normal_universe=None):
    if row.get('trade_date') != trade_date:
        raise ValueError('DATED_VALIDITY_SCOPE_REQUIRED')
    key = row.get('source_security_key')
    identifier = None if key is None else bool(isinstance(key, str) and re.fullmatch(r'(SH|SZ|BJ)\.\d{6}', key))
    # Explicit null missing_state is an observed legacy FALSE. An absent field
    # is missing source evidence and cannot be rewritten as an observed FALSE.
    expected = exact_value(key, row['missing_state']) if key is not None and 'missing_state' in row else None
    status = row.get('status')
    mapped = identifier if status in ('ACTUAL_TRADED', 'SUSPENDED') else (
        False if status in ('NOT_LISTED_YET', 'DELISTED_OR_INACTIVE') and identifier is not None else None)
    decision = 'UNKNOWN' if expected is None or mapped is None else ('PASS' if expected == mapped else 'DIFFERENCE')
    return dict(contract_id=CONTRACT, T0=trade_date, value=expected, production=False,
        original_A05_expected=expected, V2_actual=mapped, comparison=decision,
        identifier=identifier, missing_state_present='missing_state' in row,
        lifecycle_status=status, normal_universe=normal_universe,
        market_denominator=(expected and normal_universe) if expected is not None and type(normal_universe) is bool else None,
        sector_valid='REQUIRES_FULL_SECTOR_TOTAL_VALID_COUNT_AND_ROLE',
        time_role='CURRENT_SNAPSHOT_ONLY', legal_time_range=[trade_date, trade_date],
        formal_consumer_enabled=False)
