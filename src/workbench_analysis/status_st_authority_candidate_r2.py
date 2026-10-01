"""Candidate-only reconstructed provider adapter. No formal owner registration."""
from datetime import date

MODE='TARGET_DATE_QUERYABLE_FACT'
LINEAGE='RECONSTRUCTED_CORRECTED'

def bit(value):
    # Unknown, malformed and empty values never become normal/should-trade facts.
    if value in ('0',0) and not isinstance(value,bool):return 0
    if value in ('1',1) and not isinstance(value,bool):return 1
    return None

def candidate_fact(member,provider,owner,*,field,formal_use=False):
    if formal_use:raise ValueError('AUTHORITY_OWNER_NOT_EXTERNALLY_ACCEPTED')
    if owner.get('external_acceptance') is not None or owner.get('formal_consumer_authorization') is not False:
        raise ValueError('CANDIDATE_DECLARATION_INVALID')
    if owner['field_id']!=field or owner['historical_mode']!=MODE:raise ValueError('OWNER_SCOPE_INVALID')
    scope=owner['effective_scope'];day=date.fromisoformat(member['trade_date'])
    if not date.fromisoformat(scope['start_date'])<=day<=date.fromisoformat(scope['end_date']):raise ValueError('TARGET_OUT_OF_SCOPE')
    if 'captured_dates_only' in owner and day.isoformat() not in owner['captured_dates_only']:raise ValueError('FROZEN_DATED_RESPONSE_MISSING')
    keys=('security_id','source_security_key','trade_date')
    if any(member[k]!=provider[k] for k in keys):raise ValueError('DATED_IDENTITY_BINDING_MISMATCH')
    result={k:member[k] for k in keys}
    value=bit(provider.get('provider_tradestatus') if field=='TRADING_STATUS' else provider.get('is_st'))
    result.update(owner_contract_id=owner['contract_id'],knowledge_lineage=LINEAGE,historical_mode=MODE,formal_publication=False,
                  first_availability_at_target_proven=False,source_observed_at=owner['source_observed_at'],source_revision=provider.get('source_revision'),provider_value=value)
    if 'captured_observations' in owner:
        observation=next(x for x in owner['captured_observations'] if x['target_trade_date']==day.isoformat())
        result.update(source_observed_at=observation['observed_at'],source_received_at=observation['received_at'],source_revision='sha256:'+observation['response']['sha256'])
    if field=='TRADING_STATUS':
        actual=member.get('source_bar_present') is True
        result.update(status='ACTUAL_TRADED' if actual else {0:'SUSPENDED',1:'DATA_GAP'}.get(value,'UNKNOWN'),
                      status_source='LOCAL_TDX_BAR_PRESENCE' if actual else 'BAOSTOCK_DATED_RECONSTRUCTED_FIELD_CANDIDATE',
                      provider_tradestatus=provider.get('provider_tradestatus'),provider_conflict=actual and value==0,is_st=None)
    elif field=='ISST':
        result.update(is_st=None if value is None else str(value),st_state={0:'NORMAL',1:'ST_OR_STAR_ST'}.get(value,'UNKNOWN'),
                      risk_warning_taxonomy='BINARY_ST_MARKER_ONLY; DELISTING_PHASE_IS_SEPARATE_OFFICIAL_EVENT',binding_quality=provider.get('binding_quality'))
    else:raise ValueError('FIELD_OUT_OF_SCOPE')
    return result
