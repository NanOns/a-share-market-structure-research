"""Fail-closed pure frozen-cohort read contract; grants no production capability.

R3 engineering boundary for future legal Owners. Focus is never substituted.
"""
from datetime import datetime, date, timezone, timedelta
from hashlib import sha256
import json
CONTRACT='VALIDATION_COHORT_READ_R3_V2'
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
    for key in KEY+('publication_id','frozen_signal_version'):
        if not isinstance(row[key],str) or not row[key].strip():raise ValueError('NONEMPTY_FROZEN_IDENTITY_REQUIRED')
    benchmark=row['benchmark']
    if not isinstance(benchmark,dict) or not isinstance(benchmark.get('id'),str) or not benchmark['id'].strip():
        raise ValueError('BENCHMARK_IDENTITY_REQUIRED')
    if row['entity_type'] not in ('STOCK','SECTOR'):raise ValueError('COHORT_ENTITY_TYPE_REQUIRED')
    date.fromisoformat(row['T0']);date.fromisoformat(trade_date)
    if row['T0']>trade_date:raise ValueError('FUTURE_T0_FORBIDDEN')
    if row['evidence_class']!='PIT_OBSERVED' or row['cohort_namespace'] not in ('SHADOW','PRODUCTION'):raise ValueError('NO_ASOF_ENROLLMENT')
    if row['no_lookahead'] is not True or row['eligible_at_T0'] is not True:raise ValueError('INELIGIBLE_OR_LOOKAHEAD')
    frozen=instant(row['frozen_at_T0'])
    if frozen.astimezone(timezone(timedelta(hours=8))).date().isoformat()!=row['T0'] or frozen>instant(cutoff):raise ValueError('INVALID_T0_FREEZE_CUTOFF')
    if instant(row['asof_first_available'])>frozen:raise ValueError('FIRST_AVAILABLE_AFTER_T0_FREEZE')
    if instant(row['asof_first_available'])>instant(cutoff):raise ValueError('FUTURE_FIRST_AVAILABLE')
    if row.get('qualification_source') in ('Focus','UI Top-K','Forward outcome','FEP prediction') or row.get('future_outcome_in_prediction'):raise ValueError('FORBIDDEN_FEEDBACK')
    identity=enrollment_identity(row)
    if row.get('cohort_enrollment_id') not in (None,identity):raise ValueError('ENROLLMENT_IDENTITY_MISMATCH')
    return identity

def read_authorized_statistics(root, *, accepted_head, owner_binding, trade_date):
    """Read only an Owner and explicit read grant anchored in an accepted Head.

    The caller supplies the accepted Head binding from its verified API context,
    never a request body. Owner-local authorized_read is not an authority.
    R4 prepares this interface; it does not issue grants or enroll production.
    """
    from pathlib import Path
    from .r43_owner_replay import checked
    root=Path(root)
    head=json.loads(checked(root,accepted_head).read_bytes())
    if head.get('owners',{}).get(trade_date,{}).get('validation_cohort')!=owner_binding:
        raise ValueError('COHORT_ACCEPTED_OWNER_BINDING_REQUIRED')
    grant_ref=head.get('cohort_read_grants',{}).get(trade_date)
    if not grant_ref:raise ValueError('COHORT_READ_GRANT_MISSING')
    grant=json.loads(checked(root,grant_ref).read_bytes())
    owner=json.loads(checked(root,owner_binding).read_bytes())
    if (grant.get('contract_id')!='VALIDATION_COHORT_READ_GRANT_R4_V1' or
        grant.get('capability')!='READ_STATISTICS' or grant.get('authorized') is not True or
        grant.get('owner')!=owner_binding or grant.get('trade_date')!=trade_date or
        owner.get('contract_id')!=CONTRACT or owner.get('trade_date')!=trade_date):
        raise ValueError('COHORT_GRANT_OR_OWNER_IDENTITY_MISMATCH')
    result=read_statistics(dict(owner,authorized_read=True),cutoff=grant['read_cutoff'],trade_date=trade_date)
    for row in result['items']:
        if row['benchmark']['id']!=grant.get('benchmark_id') or row['frozen_signal_version']!=grant.get('frozen_signal_version'):
            raise ValueError('COHORT_FROZEN_CONTRACT_IDENTITY_MISMATCH')
        validate_source_receipt(root,head,grant,row)
    return result

def validate_source_receipt(root,head,grant,row):
    """Require exact issuance provenance, not an owner-local assertion of PIT."""
    from .r43_owner_replay import checked
    binding=grant.get('source_manifest')
    if not binding or head.get('cohort_source_manifests',{}).get(row['T0'])!=binding:
        raise ValueError('COHORT_ACCEPTED_SOURCE_MANIFEST_REQUIRED')
    manifest=json.loads(checked(root,binding).read_bytes())
    if (manifest.get('contract_id')!='COHORT_T0_SOURCE_RECEIPT_R4_V1' or
        manifest.get('publication_id')!=row['publication_id'] or
        manifest.get('T0')!=row['T0'] or manifest.get('evidence_class')!='PIT_OBSERVED'):
        raise ValueError('COHORT_SOURCE_PUBLICATION_MISMATCH')
    frozen=instant(row['frozen_at_T0'])
    for key in ('first_available','accepted_at','published_at'):
        if not manifest.get(key) or instant(manifest[key])>frozen:
            raise ValueError('COHORT_SOURCE_NOT_AVAILABLE_AT_T0')
    if instant(manifest['first_available'])!=instant(row['asof_first_available']):
        raise ValueError('COHORT_FIRST_AVAILABILITY_MISMATCH')
    if (manifest.get('membership_asof')!=row['T0'] or
        manifest.get('membership_basis')!='AS_RECORDED' or
        manifest.get('model_contract_id')!=row['model_contract_id']):
        raise ValueError('COHORT_MEMBER_ASOF_OR_MODEL_MISMATCH')
    events_ref=manifest.get('events')
    if not events_ref:raise ValueError('COHORT_EXACT_EVENT_SOURCE_REQUIRED')
    source=json.loads(checked(root,events_ref).read_bytes())
    matches=[r for r in source['events'] if enrollment_identity(r)==enrollment_identity(row)]
    if len(matches)!=1 or matches[0]!=row:raise ValueError('COHORT_FROZEN_SOURCE_EVENT_MISMATCH')

def publish_isolated_candidate(root, *, accepted_head, owner_binding, trade_date,
                               candidate_directory, sessions):
    """Prepare a no-clobber candidate; never changes Heads or production stores.

    Existing RadarCohortRuntime remains the enrollment producer. This adapter
    accepts only its independently frozen, granted owner representation and
    reuses the existing settlement session plan without a second price engine.
    """
    from pathlib import Path
    from .v4_14_replay_io import publish,digest
    from .v4_15_settlement import due_plan
    from .r43_owner_replay import checked
    directory=Path(candidate_directory)
    if directory.is_absolute() or '..' in directory.parts or directory.parts[:2]!=('docs','evidence'):
        raise ValueError('ISOLATED_EVIDENCE_DIRECTORY_REQUIRED')
    result=read_authorized_statistics(root,accepted_head=accepted_head,owner_binding=owner_binding,trade_date=trade_date)
    head=json.loads(checked(root,accepted_head).read_bytes())
    calendar_ref=head.get('cohort_calendar')
    if not calendar_ref:raise ValueError('COHORT_ACCEPTED_CALENDAR_REQUIRED')
    calendar=json.loads(checked(root,calendar_ref).read_bytes())
    if calendar.get('session_dates')!=sessions:raise ValueError('COHORT_CALENDAR_IDENTITY_MISMATCH')
    if sessions!=sorted(set(sessions)):raise ValueError('OFFICIAL_ORDERED_SESSION_CALENDAR_REQUIRED')
    plans=[]
    for row in result['items']:
        if row['T0'] not in sessions:raise ValueError('OFFICIAL_ORDERED_SESSION_CALENDAR_REQUIRED')
        plans.append(dict(enrollment_id=enrollment_identity(row),plans=due_plan(sessions,row['T0'],trade_date)))
    candidate=dict(contract_id='COHORT_ISOLATED_PUBLISHER_R4_V1',accepted_head=accepted_head,
        source_owner=owner_binding,calendar=calendar_ref,trade_date=trade_date,enrollments=result['items'],due_plans=plans,
        production=False,write_authorized=False,settlement_owner_required=True,matured_count=None,settled_count=None)
    return publish(root,(directory/(digest([accepted_head,owner_binding,trade_date])+'.json')).as_posix(),candidate)
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
