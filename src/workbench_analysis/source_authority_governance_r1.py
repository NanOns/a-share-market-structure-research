"""A10 versioned source roles, evidence-qualified availability and consumer gates."""
from __future__ import annotations
from datetime import date, datetime
from enum import Enum
from typing import Mapping

class SourceRole(str, Enum):
    CORE_AUTHORITY='CORE_AUTHORITY'
    FIELD_AUTHORITY='FIELD_AUTHORITY'
    SUPPLEMENTAL_CROSSCHECK='SUPPLEMENTAL_CROSSCHECK'
    DIAGNOSTIC_ONLY='DIAGNOSTIC_ONLY'
    RESEARCH_ONLY='RESEARCH_ONLY'

class Availability(str, Enum):
    AVAILABLE='AVAILABLE'
    LOCAL_CAPTURE_MISSING='LOCAL_CAPTURE_MISSING'
    LOCAL_ACCEPTED_ARTIFACT_MISSING='LOCAL_ACCEPTED_ARTIFACT_MISSING'
    PROVIDER_NOT_QUERIED='PROVIDER_NOT_QUERIED'
    PROVIDER_QUERY_ATTEMPTED_FAILED='PROVIDER_QUERY_ATTEMPTED_FAILED'
    PROVIDER_TARGET_DATE_EMPTY_CONFIRMED='PROVIDER_TARGET_DATE_EMPTY_CONFIRMED'
    PROVIDER_SCHEMA_MISMATCH='PROVIDER_SCHEMA_MISMATCH'
    PROVIDER_RUNTIME_UNACCEPTED='PROVIDER_RUNTIME_UNACCEPTED'
    SOURCE_NOT_YET_PUBLISHED='SOURCE_NOT_YET_PUBLISHED'
    PIT_FIRST_AVAILABILITY_UNPROVEN='PIT_FIRST_AVAILABILITY_UNPROVEN'
    PIT_HISTORICAL_STATE_NOT_RECONSTRUCTABLE='PIT_HISTORICAL_STATE_NOT_RECONSTRUCTABLE'
    CAPABILITY_DISABLED_BY_CONTRACT='CAPABILITY_DISABLED_BY_CONTRACT'

class HistoricalMode(str, Enum):
    TARGET_DATE_QUERYABLE_FACT='TARGET_DATE_QUERYABLE_FACT'
    AS_RECORDED_PIT_FACT='AS_RECORDED_PIT_FACT'
    MUTABLE_CURRENT_SNAPSHOT='MUTABLE_CURRENT_SNAPSHOT'

ERROR_TAXONOMY=('LOCAL_ACCEPTED_FREEZE_MISSING','LOCAL_SOURCE_BYTES_MISSING','PROVIDER_NOT_QUERIED',
    'PROVIDER_QUERY_FAILED','PROVIDER_TARGET_EMPTY','SOURCE_PUBLICATION_PENDING','RUNTIME_CAPABILITY_UNACCEPTED',
    'SUPPLEMENTAL_UNAVAILABLE','CORE_REQUIRED_SOURCE_UNAVAILABLE','PIT_FIRST_AVAILABILITY_UNPROVEN',
    'PIT_SOURCE_NOT_FROZEN_AT_TARGET','HISTORICAL_CATCHUP_NOT_AUTHORIZED','HISTORICAL_CATCHUP_QUERY_FAILED')

class AuthorityError(ValueError):pass

def timestamp(value):
    parsed=datetime.fromisoformat(str(value).replace('Z','+00:00'))
    if parsed.tzinfo is None:raise AuthorityError('KNOWLEDGE_TIME_REQUIRES_TIMEZONE')
    return parsed

def validate_role_contract(rule:Mapping):
    SourceRole(rule['role']);HistoricalMode(rule['historical_retrieval_mode'])
    for k in ('field_id','source_family','owner_contract_id','allowed_consumers','may_block_core',
              'may_change_core_value','may_change_core_quality','pit_requirement'):
        if k not in rule:raise AuthorityError('ROLE_CONTRACT_FIELD_MISSING:'+k)
    if not rule['field_id'] or not rule['owner_contract_id'] or not isinstance(rule['allowed_consumers'],list):
        raise AuthorityError('ROLE_CONTRACT_IDENTITY_INVALID')
    if any(type(rule[k]) is not bool for k in ('may_block_core','may_change_core_value','may_change_core_quality')):
        raise AuthorityError('ROLE_PERMISSIONS_MUST_BE_BOOLEAN')
    if rule['role'] in (SourceRole.SUPPLEMENTAL_CROSSCHECK,SourceRole.DIAGNOSTIC_ONLY,SourceRole.RESEARCH_ONLY):
        if any(rule[k] for k in ('may_block_core','may_change_core_value','may_change_core_quality')):
            raise AuthorityError('SUPPLEMENTAL_MAY_NOT_BLOCK_OR_OVERWRITE_CORE')
    return True

def validate_availability(state,target_trade_date,request_receipt=None):
    state=Availability(state);date.fromisoformat(target_trade_date)
    proof_states=(Availability.PROVIDER_QUERY_ATTEMPTED_FAILED,Availability.PROVIDER_TARGET_DATE_EMPTY_CONFIRMED,
                  Availability.PROVIDER_SCHEMA_MISMATCH)
    if state in proof_states:
        r=request_receipt or {}
        if (type(r.get('request_count')) is not int or r['request_count']<=0 or not r.get('bounded')
            or r.get('target_trade_date')!=target_trade_date or not r.get('observed_at')):
            raise AuthorityError('PROVIDER_CONCLUSION_REQUIRES_ACTUAL_BOUNDED_TARGET_REQUEST')
        timestamp(r['observed_at'])
        if state==Availability.PROVIDER_TARGET_DATE_EMPTY_CONFIRMED:
            if (r.get('provider_date')!=target_trade_date or r.get('row_count')!=0 or r.get('error_code')!='0'
                or not r.get('schema_valid') or len(str(r.get('response_sha256','')))!=64):
                raise AuthorityError('EMPTY_CONCLUSION_REQUIRES_SUCCESSFUL_EXACT_DATE_RESPONSE')
        elif state==Availability.PROVIDER_QUERY_ATTEMPTED_FAILED:
            if not r.get('error') and r.get('error_code') in (None,'0'):
                raise AuthorityError('FAILED_CONCLUSION_REQUIRES_REQUEST_FAILURE')
        elif not r.get('schema_error'):
            raise AuthorityError('SCHEMA_CONCLUSION_REQUIRES_RESPONSE_SCHEMA_FAILURE')
    return state.value

def validate_temporal_lineage(fact:Mapping,mode:HistoricalMode|str):
    mode=HistoricalMode(mode);target=date.fromisoformat(fact['target_trade_date'])
    if fact.get('provider_date')!=target.isoformat():raise AuthorityError('PROVIDER_TARGET_DATE_MISMATCH')
    observed=timestamp(fact['observed_at']);received=timestamp(fact['received_at'])
    if received<observed:raise AuthorityError('RECEIVED_TIME_PRECEDES_OBSERVATION')
    if observed.date()<target:raise AuthorityError('OBSERVATION_PRECEDES_TARGET_FACT')
    if mode==HistoricalMode.TARGET_DATE_QUERYABLE_FACT:
        if observed.date()>target:
            if fact.get('origin')!='DELAYED_HISTORICAL_RETRIEVAL':raise AuthorityError('DELAYED_ORIGIN_REQUIRED')
            if fact.get('AS_RECORDED_AT_CLOSE') or fact.get('lineage')=='AS_RECORDED':raise AuthorityError('CATCHUP_CANNOT_PROVE_AS_RECORDED')
            if fact.get('first_available_at') is not None:raise AuthorityError('CATCHUP_CANNOT_MINT_FIRST_AVAILABILITY')
    elif mode==HistoricalMode.MUTABLE_CURRENT_SNAPSHOT:
        if observed.date()>target and fact.get('lineage') not in ('CURRENT_MEMBERSHIP_REPLAY','DIAGNOSTIC'):
            raise AuthorityError('MUTABLE_CURRENT_SNAPSHOT_CANNOT_BACKDATE_PIT')
    else:
        if not fact.get('first_availability_evidence') or not fact.get('source_revision') or not fact.get('first_available_at'):
            raise AuthorityError('PIT_FIRST_AVAILABILITY_UNPROVEN')
        known=timestamp(fact['first_available_at'])
        if known>timestamp(fact['knowledge_cutoff']):raise AuthorityError('PIT_KNOWLEDGE_AFTER_CUTOFF')
    return True

def evaluate_consumer_gate(rule:Mapping,*,consumer_contract_id,availability,target_trade_date,
                           core_value=None,supplemental_value=None,request_receipt=None,required=False):
    validate_role_contract(rule)
    state=validate_availability(availability,target_trade_date,request_receipt)
    if rule.get('enabled') is False:state=Availability.CAPABILITY_DISABLED_BY_CONTRACT.value
    declared=consumer_contract_id in rule['allowed_consumers']
    authority=rule['role'] in (SourceRole.CORE_AUTHORITY,SourceRole.FIELD_AUTHORITY)
    if required and not authority:raise AuthorityError('SUPPLEMENTAL_MAY_NOT_BLOCK_CORE')
    if required and not declared:raise AuthorityError('UNDECLARED_CONSUMER_DEPENDENCY')
    missing=state!=Availability.AVAILABLE
    return dict(contract_id='SOURCE_AUTHORITY_CONSUMER_GATE_R1',field_id=rule['field_id'],consumer_contract_id=consumer_contract_id,
        status='BLOCKED_DECLARED_CAPABILITY' if required and missing and rule['may_block_core'] else 'PASS_CORE_SCOPE',
        capability_blocked=bool(required and missing and rule['may_block_core']),availability=state,
        core_value=(supplemental_value if authority and declared and rule['may_change_core_value'] and not missing else core_value),
        core_quality_changed=False,supplement_quality='AVAILABLE' if not missing else 'UNAVAILABLE',
        crosscheck=('UNKNOWN' if missing else 'MATCH' if supplemental_value==core_value else 'CONFLICT'),
        source_role=rule['role'],global_core_blocked=False)
