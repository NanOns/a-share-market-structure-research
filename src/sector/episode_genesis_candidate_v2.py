"""Creation-bound sector episode candidate; bytes never confer admission."""
from datetime import datetime, timezone, timedelta
import json
import math

from .d2_admission_candidate_r4 import instant
from .operational_candidate_v1 import evaluate_invalidation, followup
from workbench_analysis.v4_14_replay_io import exact, publish, digest
from workbench_analysis.v4_15_settlement import due_plan

CONTRACT = 'SECTOR_EPISODE_GENESIS_CANDIDATE_V2'


def create(root, *, capture_binding, membership_binding, conditions_binding,
           priority_binding, price_binding, calendar_binding, sector_id, cutoff):
    """Consume original bindings, freezing membership/AST/scenario/due plan.

    Only current actual clock is used. Synthetic fixtures must declare their
    evidence class; neither observed candidates nor fixtures activate D2.
    """
    bindings = dict(capture=capture_binding, membership=membership_binding,
                    conditions=conditions_binding, priority=priority_binding,
                    price=price_binding, calendar=calendar_binding)
    docs = {key: json.loads(exact(root, value)) for key, value in bindings.items()}
    now = datetime.now(timezone.utc)
    target = instant(cutoff).astimezone(timezone(timedelta(hours=8))).date().isoformat()
    if instant(cutoff) > now or target != now.astimezone(timezone(timedelta(hours=8))).date().isoformat():
        raise ValueError('CURRENT_REAL_GENESIS_CLOCK_REQUIRED_NO_BACKFILL')
    capture, member, condition, priority, price, calendar = (docs[key] for key in bindings)
    sessions = calendar['session_dates']
    if sessions != sorted(set(sessions)) or target not in sessions:
        raise ValueError('EXACT_GENESIS_CALENDAR_REQUIRED')
    synthetic = capture.get('evidence_class') == 'SYNTHETIC_ISOLATED_TEST_ONLY'
    if capture.get('evidence_class') not in ('CURRENT_OBSERVATION_CANDIDATE', 'SYNTHETIC_ISOLATED_TEST_ONLY') or capture.get('gaps'):
        raise ValueError('GENESIS_CURRENT_SOURCE_REQUIRED')
    for key in ('capture', 'membership', 'price'):
        doc = docs[key]
        if (doc.get('T0') != target or doc.get('sector_id') != sector_id or
                not doc.get('first_available') or instant(doc['first_available']) > instant(cutoff)):
            raise ValueError('GENESIS_SOURCE_IDENTITY_OR_FIRST_CLOCK:' + key)
    if (not capture.get('received_at') or not capture.get('captured_at') or
            not instant(capture['received_at']) <= instant(capture['captured_at']) <= instant(cutoff) or
            instant(capture['first_available']) > instant(capture['received_at'])):
        raise ValueError('GENESIS_REQUEST_RECEIPT_CLOCK_REQUIRED')
    members = member.get('member_ids', [])
    if (not members or len(members) != len(set(members)) or member.get('AS_RECORDED') is not True or
            not member.get('member_set_asof') or capture.get('membership') != membership_binding or
            sorted(capture.get('member_ids', [])) != sorted(members) or price.get('source_capture') != capture_binding):
        raise ValueError('CREATION_BOUND_SECTOR_MEMBERSHIP_REQUIRED')
    for key in ('conditions', 'priority', 'calendar'):
        doc = docs[key]
        if not doc.get('contract_id') or not doc.get('version') or not doc.get('first_available') or instant(doc['first_available']) > instant(cutoff):
            raise ValueError('GENESIS_VERSIONED_CONTRACT_CLOCK_REQUIRED:' + key)
    if (not condition.get('conditions') or not condition.get('rules') or
            condition.get('rule_id') not in condition['rules']):
        raise ValueError('GENESIS_FROZEN_INVALIDATION_AST_REQUIRED')
    order = priority.get('scenario_priority', [])
    matched = capture.get('matched_scenarios', [])
    if (not order or len(order) != len(set(order)) or not matched or
            len(matched) != len(set(matched)) or not set(matched) <= set(order)):
        raise ValueError('GENESIS_FROZEN_SCENARIO_PRIORITY_REQUIRED')
    value = price.get('price')
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
        raise ValueError('GENESIS_FINITE_PRICE_REQUIRED')
    identity = digest([CONTRACT, target, sector_id, capture_binding])
    document = dict(contract_id=CONTRACT, episode_id=identity, T0=target,
        sector_id=sector_id, entity_id=sector_id, entity_type='SECTOR', trade_date=target,
        first_available=capture['captured_at'], frozen_members=sorted(members),
        member_ids=sorted(members), member_set_asof=member['member_set_asof'],
        AS_RECORDED=True, invalidation_contract=conditions_binding,
        invalidation_contract_id=condition['contract_id'], invalidation_contract_sha256=conditions_binding['sha256'],
        frozen_conditions=condition['conditions'], frozen_rules=condition['rules'],
        scenario=next(item for item in order if item in matched),
        matched_scenarios=matched, scenario_priority=priority_binding,
        frozen_price=value, sources=bindings, due_plan=due_plan(sessions, target, target),
        evidence_class='SYNTHETIC_ISOLATED_TEST_ONLY' if synthetic else 'CURRENT_OBSERVATION_CANDIDATE',
        production=False, formal_consumer_enabled=False, formal_D2='NOT_GRANTED')
    return publish(root, f'data/v4/sector_episode_candidates_v2/{identity}/genesis.json', document)


def observe(root, *, episode_binding=None, facts=None, trade_date, calendar_binding, settlement=None):
    """Missing episode and missing due settlement remain explicit."""
    if episode_binding is None:
        return dict(status='NO_PRIOR_EPISODE', frozen_invalidation=None,
                    followup_complete=None, followup_status='NO_PRIOR_EPISODE',
                    next_due_date=None, unknown_due_reasons=[], formal_D2='NOT_GRANTED')
    episode = json.loads(exact(root, episode_binding))
    calendar = json.loads(exact(root, calendar_binding))
    if episode.get('contract_id') != CONTRACT or episode['sources']['calendar'] != calendar_binding:
        raise ValueError('GENESIS_CALENDAR_OR_CONTRACT_CHANGED')
    for source in episode['sources'].values():
        exact(root, source)
    sessions = calendar['session_dates']
    today = datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=8))).date().isoformat()
    if episode['evidence_class'] != 'SYNTHETIC_ISOLATED_TEST_ONLY' and trade_date > today:
        raise ValueError('REAL_FUTURE_EPISODE_OBSERVATION_REJECTED')
    for horizon, binding in (settlement or {}).items():
        item = json.loads(exact(root, binding))
        if (not item.get('first_available') or instant(item['first_available']) > datetime.now(timezone.utc) or
                item.get('trade_date', '9999') > trade_date or
                item.get('member_ids') != episode['member_ids']):
            raise ValueError('SETTLEMENT_CLOCK_OR_CREATION_MEMBERS_REQUIRED')
    invalid = evaluate_invalidation(root, episode_binding, facts or {}, trade_date=trade_date, sessions=sessions)
    outcomes = followup(episode, trade_date=trade_date, sessions=sessions, settlement=settlement, root=root)
    complete = 'TRUE' if all(item['status'] == 'COMPLETE' for item in outcomes.values()) else 'UNKNOWN'
    reasons = [dict(horizon=key, due_date=item['due_date'],
                    reason='CALENDAR_HORIZON_UNAVAILABLE' if item['due_date'] is None else 'DUE_SETTLEMENT_SOURCE_MISSING_OR_WRONG_EPISODE')
               for key, item in outcomes.items()
               if item['status'] == 'UNKNOWN' or item['due_date'] is None]
    status = ('UNKNOWN' if reasons else 'COMPLETE' if complete == 'TRUE' else 'PENDING')
    next_dates = [item['due_date'] for item in outcomes.values()
                  if item['status'] == 'PENDING' and item['due_date'] is not None]
    return dict(status='EPISODE_CANDIDATE', evidence_class=episode['evidence_class'], frozen_invalidation=invalid,
                followup=outcomes, followup_complete=complete, followup_status=status,
                next_due_date=min(next_dates) if next_dates else None,
                unknown_due_reasons=reasons, formal_D2='NOT_GRANTED', production=False)
