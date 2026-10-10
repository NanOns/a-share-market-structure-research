"""Exact extracted legacy eligibility; accepted observation gate is separate."""
import re
import math

CONTRACT_ID='LEGACY_VALID_MEMBER_EXACT_PRODUCER_V1'
LEGACY_VERSION='sector-factor-contract-v1.1-correctness'
EXCLUDED=('FILE_MISSING','DELISTED_OR_INACTIVE')

def exact_value(source_security_id, missing_state):
    # This preserves phase2.prepare semantics, including unknown non-null strings,
    # suspended stocks and NOT_LISTED_YET. It is not a newly designed trading gate.
    missing=missing_state is None or isinstance(missing_state,float) and math.isnan(missing_state)
    return bool(isinstance(source_security_id,str) and re.fullmatch(r'(SH|SZ|BJ)\.\d{6}',source_security_id) and not missing and missing_state not in EXCLUDED)

def produce(row, *, trade_date, source_binding, accepted_observation=False):
    if accepted_observation: raise ValueError('A05_INDEPENDENT_EXTERNAL_ACCEPTANCE_REQUIRED')
    if not source_binding.get('sha256') or not source_binding.get('path'):
        raise ValueError('LEGACY_VALID_MEMBER_SOURCE_BINDING_REQUIRED')
    if row.get('trade_date') != trade_date: raise ValueError('LEGACY_VALID_MEMBER_TIME_ROLE_MISMATCH')
    missing=row.get('missing_state')
    value=exact_value(row.get('source_security_id'),missing)
    return dict(value=value,quality='CANDIDATE',producer_contract=LEGACY_VERSION,extracted_producer_contract=CONTRACT_ID,source_binding=source_binding,trade_date=trade_date,max_source_date=trade_date,time_role='CURRENT_SNAPSHOT_ONLY',legacy_equivalent=True,production=False)
