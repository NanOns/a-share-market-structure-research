"""Isolated SECTOR extraction candidate. No accepted producer or write authority.

The existing research_state reducer remains the only D2 reducer. This adapter
reports readiness and refuses to invent its six unadmitted upstream fields.
"""
from datetime import datetime, timezone, timedelta
import hashlib
import json
import re

CONTRACT = 'SECTOR_D2_EXTRACTION_CANDIDATE_R4_R1'
FIELDS = ('CONFIRMED', 'WARM', 'frozen_invalidation',
          'episode_invalidation_contract_id', 'followup_complete', 'scenario')

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    separators=(',', ':')).encode()).hexdigest()

def instant(value):
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None:
        raise ValueError('AWARE_FIRST_AVAILABLE_REQUIRED')
    return result

def extract(native, *, source_binding, cutoff, upstream=None, prior=None, sessions=None):
    """Extract dated operational dq5; upstream values need exact source receipts.

    Supplied receipts are candidate inputs only, never authorization. A real
    admission must independently resolve every receipt through an accepted ledger.
    """
    if native.get('entity_type', 'SECTOR') != 'SECTOR':
        raise ValueError('SECTOR_ENTITY_REQUIRED')
    members = native['member_ids']
    if len(members) != len(set(members)):
        raise ValueError('UNIQUE_MEMBER_DENOMINATOR_REQUIRED')
    target = native['trade_date']
    if instant(cutoff).astimezone(timezone(timedelta(hours=8))).date().isoformat() != target:
        raise ValueError('TARGET_CUTOFF_MISMATCH')
    if not source_binding.get('sha256') or not source_binding.get('path'):
        raise ValueError('SOURCE_BYTES_BINDING_REQUIRED')
    if prior:
        if (not sessions or sessions != sorted(set(sessions)) or target not in sessions or
            sessions.index(target)==0 or prior['entity_id'] != native['sector_id'] or
            prior['trade_date'] != sessions[sessions.index(target)-1]):
            raise ValueError('EXACT_PRIOR_SESSION_REQUIRED')
    facts = {}
    for field in FIELDS:
        receipt = (upstream or {}).get(field)
        reason = 'SOURCE_NOT_PRESENT'
        value = None
        if receipt:
            needed = {'source_sha256', 'producer_contract_id', 'parameter_set_id',
                      'first_available', 'trade_date', 'value', 'quality', 'window_identity'}
            if needed - receipt.keys():
                reason = 'INCOMPLETE_PRODUCER_RECEIPT'
            elif (not re.fullmatch('[0-9a-f]{64}',str(receipt['source_sha256'])) or
                  not all(receipt[k] for k in ('producer_contract_id','parameter_set_id','window_identity'))):
                reason = 'INVALID_PRODUCER_IDENTITY'
            elif instant(receipt['first_available']) > instant(cutoff):
                reason = 'FIRST_AVAILABLE_AFTER_CUTOFF'
            elif receipt['trade_date'] != (prior['trade_date'] if field in
                    ('frozen_invalidation', 'episode_invalidation_contract_id') and prior else target):
                reason = 'WRONG_TIME_ROLE'
            elif receipt['quality'] != 'ACCEPTED':
                reason = 'REQUIRED_QUALITY_UNAVAILABLE'
            elif field in ('CONFIRMED','WARM','frozen_invalidation','followup_complete') and receipt['value'] not in ('TRUE','FALSE','UNKNOWN'):
                reason = 'INVALID_TRI_VALUE'
            elif receipt['value'] in (None,'UNKNOWN',''):
                reason = 'REQUIRED_VALUE_UNKNOWN'
            elif field == 'frozen_invalidation' and (not prior or not prior.get('episode_id') or
                    receipt.get('episode_id') != prior['episode_id'] or
                    receipt.get('invalidation_contract_sha256') != prior.get('invalidation_contract_sha256')):
                reason = 'CREATION_FROZEN_EPISODE_MISMATCH'
            elif field == 'WARM' and receipt.get('amount_a_required') and not receipt.get('strict_h21_verified'):
                reason = 'STRICT_AMOUNT_A_HISTORY_UNVERIFIABLE'
            elif field == 'followup_complete' and (not receipt.get('due_plan') or
                    receipt.get('right_censored') or not receipt.get('settled_owner_sha256')):
                reason = 'DUE_OR_SETTLEMENT_OWNER_NOT_PRESENT'
            else:
                value, reason = receipt['value'], 'CANDIDATE_ONLY_NOT_FORMALLY_ADMITTED'
        facts[field] = dict(value=value, quality='UNKNOWN' if value is None else 'CANDIDATE',
                            reason=reason, source_receipt=receipt)
    missing = [key for key, fact in facts.items() if fact['value'] is None]
    return dict(contract_id=CONTRACT, entity_type='SECTOR', entity_id=native['sector_id'],
        trade_date=target, member_ids=sorted(members), unique_member_count=len(members),
        member_set_asof=native.get('member_set_asof'), source_binding=source_binding,
        dq5=native['fields'].get('dq5'), upstream=facts, missing_fields=missing,
        readiness='SOURCE_INCOMPLETE' if missing else 'CANDIDATE_INPUT_COMPLETE',
        maturity=None, health=None, accepted=False, formal_consumer_enabled=False,
        reducer='src/v4/research_state.py::reduce_state',
        reducer_invoked=False, reason='FORMAL_ENTRY_ADMISSION_REQUIRED')

def freeze_episode(*, entity_id, trade_date, member_ids, contract_binding, conditions, first_available):
    if len(member_ids) != len(set(member_ids)) or not member_ids:
        raise ValueError('UNIQUE_MEMBER_DENOMINATOR_REQUIRED')
    if instant(first_available).astimezone(timezone(timedelta(hours=8))).date().isoformat() < trade_date:
        raise ValueError('CREATION_FIRST_AVAILABLE_INVALID')
    if set(contract_binding) != {'contract_id', 'version', 'sha256'} or not all(contract_binding.values()):
        raise ValueError('CREATION_CONTRACT_BINDING_REQUIRED')
    if not re.fullmatch('[0-9a-f]{64}',contract_binding['sha256']):
        raise ValueError('CREATION_CONTRACT_BINDING_REQUIRED')
    payload = dict(entity_type='SECTOR', entity_id=entity_id, trade_date=trade_date,
        member_ids=sorted(member_ids), invalidation_contract=contract_binding,
        conditions=conditions, first_available=first_available, production_authorized=False)
    return dict(payload, episode_id='SECTOR_EP_CANDIDATE:'+digest(payload))

def observe_episode(episode, *, trade_date, session_index, invalidated, previous=None):
    """Immutable candidate event identity; same-session conflicts fail closed."""
    if type(invalidated) is not bool:
        raise ValueError('EXPLICIT_INVALIDATION_REQUIRED')
    if trade_date < episode['trade_date'] or type(session_index) is not int or session_index < 0:
        raise ValueError('EPISODE_SESSION_LINEAGE_MISMATCH')
    if previous and (previous['episode_id'] != episode['episode_id'] or session_index < previous['session_index']):
        raise ValueError('EPISODE_SESSION_LINEAGE_MISMATCH')
    event = dict(episode_id=episode['episode_id'], trade_date=trade_date,
                 session_index=session_index, invalidated=invalidated,
                 reentry_allowed=False if invalidated else None,
                 frozen_contract=episode['invalidation_contract'])
    if previous and session_index == previous['session_index'] and event != previous:
        raise ValueError('SAME_SESSION_CONFLICT')
    return event
