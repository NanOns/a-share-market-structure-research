"""Fail-closed pure frozen-cohort read contract; grants no production capability.

R3 engineering boundary for future legal Owners. Focus is never substituted.
"""
from datetime import datetime
from hashlib import sha256
import json
CONTRACT='VALIDATION_COHORT_READ_R3_V1'
KEY=('model_contract_id','state_lineage_id','entity_type','entity_id','episode_id','event_type','T0')
REQUIRED=KEY+('publication_id','frozen_signal_version','frozen_at_T0','eligible_at_T0','asof_first_available','benchmark','no_lookahead','evidence_class','cohort_namespace')
def instant(s):
    d=datetime.fromisoformat(s.replace('Z','+00:00'))
    if d.tzinfo is None:raise ValueError('AWARE_FIRST_AVAILABLE_REQUIRED')
    return d
def enrollment_identity(row):
    if any(not row.get(k) for k in KEY):raise ValueError('COMPLETE_EVENT_IDENTITY_REQUIRED')
    return sha256(json.dumps([row[k] for k in KEY],ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
def validate_frozen(row,*,cutoff,trade_date):
    if any(k not in row for k in REQUIRED):raise ValueError('FROZEN_COHORT_FIELDS_MISSING')
    if row['T0']>trade_date:raise ValueError('FUTURE_T0_FORBIDDEN')
    if row['evidence_class']!='PIT_OBSERVED' or row['cohort_namespace'] not in ('SHADOW','PRODUCTION'):raise ValueError('NO_ASOF_ENROLLMENT')
    if row['no_lookahead'] is not True or row['eligible_at_T0'] is not True:raise ValueError('INELIGIBLE_OR_LOOKAHEAD')
    frozen=instant(row['frozen_at_T0'])
    if frozen.date().isoformat()!=row['T0'] or frozen>instant(cutoff):raise ValueError('INVALID_T0_FREEZE_CUTOFF')
    if instant(row['asof_first_available'])>frozen:raise ValueError('FIRST_AVAILABLE_AFTER_T0_FREEZE')
    if instant(row['asof_first_available'])>instant(cutoff):raise ValueError('FUTURE_FIRST_AVAILABLE')
    if row.get('qualification_source') in ('Focus','UI Top-K','Forward outcome','FEP prediction') or row.get('future_outcome_in_prediction'):raise ValueError('FORBIDDEN_FEEDBACK')
    identity=enrollment_identity(row)
    if row.get('cohort_enrollment_id') not in (None,identity):raise ValueError('ENROLLMENT_IDENTITY_MISMATCH')
    return identity
def maturity_schedule(t0,sessions,cutoff_date,horizons=(1,3,5)):
    if sessions!=sorted(set(sessions)) or t0 not in sessions:raise ValueError('OFFICIAL_ORDERED_SESSION_CALENDAR_REQUIRED')
    index=sessions.index(t0);result={}
    for n in horizons:
        if type(n) is not int or n<=0:raise ValueError('POSITIVE_SESSION_HORIZON_REQUIRED')
        due=sessions[index+n] if index+n<len(sessions) else None
        result[n]=dict(due_date=due,status='CALENDAR_HORIZON_UNAVAILABLE' if due is None else 'PENDING' if due>cutoff_date else 'DUE_REQUIRES_SETTLEMENT_OWNER')
    return result
def read_statistics(owner,*,cutoff,trade_date):
    if owner is None:return dict(contract_id=CONTRACT,status='NO_AUTHORIZED_COHORT_OWNER',items=[],observed_count=None,matured_count=None,write_authorized=False)
    if owner.get('authorized_read') is not True:raise ValueError('COHORT_READ_PERMISSION_MISSING')
    seen={};items=[]
    for row in owner['enrollments']:
        key=validate_frozen(row,cutoff=cutoff,trade_date=trade_date)
        if key in seen:
            if seen[key]!=row:raise ValueError('FROZEN_ENROLLMENT_REWRITE_FORBIDDEN')
            continue
        seen[key]=row;items.append(row)
    # Outcome counts require separate settlement provenance; no wall-clock inference.
    return dict(contract_id=CONTRACT,status='READY',items=items,observed_count=len(items),matured_count=None,maturity_status='SETTLEMENT_OWNER_REQUIRED',write_authorized=False)
