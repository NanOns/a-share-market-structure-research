"""Read-only, fail-closed reason attribution for candidate D0/D2 owners."""
from collections import Counter
import gzip
import json

from workbench_analysis.r43_owner_replay import checked
from workbench_analysis.r7_frozen_invalidation_v2 import evaluate_frozen_invalidation


CONTRACT_ID = 'R6_D0_REASON_ATTRIBUTION_R1'


def _load_jsonl(root, binding):
    path = checked(root, binding)
    with gzip.open(path, 'rt', encoding='utf-8') as stream:
        payload=stream.read()
    try:
        value=json.loads(payload)
        return value.get('rows',[]) if isinstance(value,dict) else value
    except json.JSONDecodeError:
        return [json.loads(line) for line in payload.splitlines() if line.strip()]


def candidate_d0_reason_attribution(root, candidate, day, *, focus_security_ids=None):
    """Summarize actual D0 scenario checks without changing eligibility states."""
    if day > '2026-10-14':
        raise ValueError('R6_DATA_CUTOFF_EXCEEDED')
    binding = candidate.get('owners', {}).get(day, {}).get('prewatch')
    if not binding:
        return dict(contract_id=CONTRACT_ID, status='SOURCE_INCOMPLETE', trade_date=day,
                    reason='CANDIDATE_D0_OWNER_NOT_BOUND', items=None)
    rows = _load_jsonl(root, binding)
    # Audit source sealing separately from the source's row-level booleans.
    # A 64-hex producer/source digest plus a valid Owner binding is not an
    # availability-time seal; keep candidate predicates diagnostic until the
    # full cutoff and permission chain is present.
    scenario_governance = {}
    for scenario in ('LAUNCH_CONFIRM','RECOVERY_TURN','STRONG_PULLBACK','TREND_CONTINUE'):
        observed=[]
        for row in rows:
            confirmation=row.get('confirmation') or {}
            for evidence in confirmation.get('scenario_evidence') or []:
                if evidence.get('scenario')==scenario:observed.append((row,evidence))
        digests={((row.get('confirmation') or {}).get('source_sha256')) for row,_ in observed}
        digest_proof=bool(digests) and all(isinstance(value,str) and len(value)==64 and
            all(char in '0123456789abcdef' for char in value.lower()) for value in digests)
        if scenario in ('LAUNCH_CONFIRM','RECOVERY_TURN'):
            status=('OPEN_SOURCE_SEAL_METADATA_MISSING' if observed else 'SOURCE_INCOMPLETE')
            role='CANDIDATE_PREDICATE_DIAGNOSTIC_ONLY'
        else:
            status='DIAGNOSTIC_ONLY'
            role='NOT_IN_FORMAL_D0_AGGREGATION'
        scenario_governance[scenario]=dict(status=status,role=role,observed_rows=len(observed),
            source_owner_digest_verified=True,producer_output_digest_present=digest_proof,
            availability_time_proven=False,cutoff_proven=False,permission_chain_proven=False,
            d0_row_predicates_preserved=True)
    overall = Counter()
    scenario_states = Counter()
    failed_checks = Counter()
    unknown_reasons = Counter()
    prewatch_states = Counter()
    prewatch_unknowns = Counter()
    focus_triggers = 0
    focus_ids = {str(value) for value in (focus_security_ids or []) if value}
    focus_d0 = Counter()
    focus_d0_reasons = Counter()
    d0_by_security = {}
    for row in rows:
        if row.get('trade_date') != day:
            raise ValueError('R6_D0_ROW_DATE_MISMATCH')
        confirmation = row.get('confirmation') or {}
        overall[str(confirmation.get('confirmation_status') or 'UNKNOWN')] += 1
        for item in confirmation.get('scenario_evidence') or []:
            scenario = str(item.get('scenario') or 'UNKNOWN')
            status = str(item.get('status') or 'UNKNOWN')
            scenario_states[f'{scenario}:{status}'] += 1
            checks = item.get('checks') or {}
            for name, value in checks.items():
                if value is False:
                    failed_checks[f'{scenario}:{name}'] += 1
            for reason in item.get('unknown_reasons') or []:
                unknown_reasons[f'{scenario}:{reason}'] += 1
        prewatch = row.get('prewatch') or {}
        prewatch_states[str(prewatch.get('raw_qualification') or 'UNKNOWN')] += 1
        for item in prewatch.get('unknown_predicates') or []:
            prewatch_unknowns[str(item)] += 1
        focus_triggers += int(bool((row.get('signals') or {}).get('focus_trigger')))
        security_id=str(row.get('security_id') or row.get('entity_id') or '')
        if security_id:
            d0_by_security[security_id] = row
            if security_id in focus_ids:
                focus_d0[str(confirmation.get('confirmation_status') or 'UNKNOWN')] += 1
                for item in confirmation.get('scenario_evidence') or []:
                    scenario = str(item.get('scenario') or 'UNKNOWN')
                    for reason in item.get('unknown_reasons') or []:
                        focus_d0_reasons[f'{scenario}:{reason}'] += 1
                    for check, value in (item.get('checks') or {}).items():
                        if value is False:
                            focus_d0_reasons[f'{scenario}:FAILED:{check}'] += 1
    focus_d2 = Counter()
    focus_d2_reasons = Counter()
    d2_by_security = {}
    r7_invalidation_states = Counter()
    r7_invalidation_reasons = Counter()
    r7_invalidation_examples = []
    prior_rows = {}
    d2_binding = candidate.get('owners', {}).get(day, {}).get('focus')
    if focus_ids and d2_binding:
        published=candidate.get('published_sessions',[])
        day_index=published.index(day) if day in published else -1
        prior_day=published[day_index-1] if day_index>0 else None
        prior_binding=candidate.get('owners',{}).get(prior_day,{}).get('focus') if prior_day else None
        prior_rows={str(x.get('entity_id') or x.get('security_id')):x for x in _load_jsonl(root,prior_binding)} if prior_binding else {}
        for row in _load_jsonl(root, d2_binding):
            security_id = str(row.get('security_id') or row.get('entity_id') or '')
            if security_id not in focus_ids:
                continue
            d2_by_security[security_id]=row
            focus_d2[str(row.get('final_eligibility') or 'UNKNOWN')] += 1
            for reason in row.get('unknown_predicates') or []:
                focus_d2_reasons[str(reason)] += 1
            provenance = row.get('input_provenance') or {}
            invalidation = provenance.get('frozen_invalidation') or {}
            if invalidation.get('status') == 'NOT_IMPLEMENTED':
                focus_d2_reasons['frozen_invalidation:REQUIRED_INPUT_NOT_IMPLEMENTED'] += 1
            prior=prior_rows.get(security_id)
            prior_episode={'episode_id':prior.get('episode_id'),
                'invalidation_contract_id':prior.get('invalidation_contract_id')} if prior and prior.get('episode_id') else None
            evaluated=evaluate_frozen_invalidation(prior_episode=prior_episode,current_close=None,
                frozen_invalidation_level=None,current_price_basis_id=None,frozen_price_basis_id=None,
                current_bar_status='UNKNOWN',current_source_sha256=None,trade_date=day,source_trade_date=day)
            r7_invalidation_states['NOT_APPLICABLE' if evaluated['status']=='NOT_APPLICABLE' else evaluated['value']]+=1
            if evaluated.get('reason'):r7_invalidation_reasons[evaluated['reason']]+=1
            if len(r7_invalidation_examples)<5:
                r7_invalidation_examples.append(dict(entity_id=security_id,prior_episode_id=(prior or {}).get('episode_id'),
                    prior_invalidation_contract_id=(prior or {}).get('invalidation_contract_id'),
                    legacy_status=invalidation.get('status'),r7_candidate=evaluated))
    forward_binding=candidate.get('owners',{}).get(day,{}).get('forward')
    forward_capture={}
    if forward_binding:
        forward_path=checked(root,forward_binding)
        with gzip.open(forward_path,'rt',encoding='utf-8') as stream:forward_payload=json.load(stream)
        forward_capture={str(row.get('entity_id')):bool(row.get('HISTORICAL_FIRST_AVAILABLE_PROVEN'))
                         for row in forward_payload.get('episodes',[]) if row.get('entity_id')}
    focus_primary_reasons=Counter()
    focus_primary_reason_rule={
        'D0_UNKNOWN':'D0 confirmation status is UNKNOWN or the D0 row is absent',
        'D2_FROZEN_INVALIDATION_UNKNOWN':'D0 is TRUE, D2 is UNKNOWN, and the prior episode lacks a supported invalidation contract/level',
        'D2_OTHER_UNKNOWN':'D0 is TRUE but D2 remains UNKNOWN for a different required input',
        'QUALIFICATION_FALSE':'D2 is explicitly FALSE',
        'SIGNAL_NOT_TRIGGERED':'D0 is explicitly FALSE',
        'FIRST_CAPTURE_NOT_PROVEN':'D0 and D2 are TRUE but no historical first-capture proof exists',
        'OTHER_EVIDENCE_GAP':'No preceding mutually exclusive rule explains the row',
    }
    for security_id in focus_ids:
        d0_row=d0_by_security.get(security_id);d0_state=((d0_row or {}).get('confirmation') or {}).get('confirmation_status','MISSING')
        d2_row=d2_by_security.get(security_id);d2_state=(d2_row or {}).get('final_eligibility','MISSING')
        if d0_state!='TRUE':reason='D0_UNKNOWN' if d0_state not in ('FALSE',) else 'SIGNAL_NOT_TRIGGERED'
        elif d2_state=='FALSE':reason='QUALIFICATION_FALSE'
        elif d2_state=='UNKNOWN':
            prev=prior_rows.get(security_id)
            invalidation=((d2_row or {}).get('input_provenance') or {}).get('frozen_invalidation') or {}
            reason='D2_FROZEN_INVALIDATION_UNKNOWN' if prev and prev.get('episode_id') and invalidation.get('status')=='NOT_IMPLEMENTED' else 'D2_OTHER_UNKNOWN'
        elif d2_state=='TRUE' and not forward_capture.get(security_id,False):reason='FIRST_CAPTURE_NOT_PROVEN'
        else:reason='OTHER_EVIDENCE_GAP'
        focus_primary_reasons[reason]+=1
    focus_summary = dict(focus_denominator=len(focus_ids),
        d0_mapped=sum(focus_d0.values()),d0_confirmation_status_counts=dict(sorted(focus_d0.items())),
        d0_top_reason_counts=[dict(reason=k,count=v) for k,v in focus_d0_reasons.most_common(20)],
        d2_mapped=sum(focus_d2.values()),d2_final_eligibility_counts=dict(sorted(focus_d2.items())),
        d2_top_reason_counts=[dict(reason=k,count=v) for k,v in focus_d2_reasons.most_common(20)],
        r7_frozen_invalidation=dict(contract_id='FROZEN_INVALIDATION_CONTRACT_R2',
            candidate_states=dict(sorted(r7_invalidation_states.items())),
            candidate_reasons=[dict(reason=k,count=v) for k,v in r7_invalidation_reasons.most_common()],
            samples=r7_invalidation_examples,production_admission=False,AS_RECORDED=False,PIT_ELIGIBLE=False),
        primary_reason_contract='R7_FOCUS_PRIMARY_REASON_V1',
        primary_reason_rule_order=list(focus_primary_reason_rule),
        primary_reason_definitions=focus_primary_reason_rule,
        primary_reason_counts=dict(sorted(focus_primary_reasons.items())),
        primary_reason_total=sum(focus_primary_reasons.values()),
        source=d2_binding)
    return dict(contract_id=CONTRACT_ID, version='1.0.0', status='READY', trade_date=day,
        total=len(rows), confirmation_status_counts=dict(sorted(overall.items())),
        scenario_status_counts=dict(sorted(scenario_states.items())),
        most_common_failed_checks=[dict(reason=k,count=v) for k,v in failed_checks.most_common(20)],
        unknown_reasons=[dict(reason=k,count=v) for k,v in unknown_reasons.most_common(20)],
        prewatch_qualification_counts=dict(sorted(prewatch_states.items())),
        prewatch_unknown_predicates=[dict(reason=k,count=v) for k,v in prewatch_unknowns.most_common(20)],
        scenario_governance=dict(contract_id='V4_D0_CANDIDATE_GOVERNANCE_AUDIT_R1',version='1.0.0',
            source_binding=binding,scenarios=scenario_governance,
            diagnostic_unknown_absorbed_into_formal_candidate=False,
            D0_status_values_unchanged=True),
        focus_trigger_count=focus_triggers,focus_intersection=focus_summary,source=binding,
        AS_RECORDED=False,PIT_ELIGIBLE=False,eligibility_mutated=False,
        scope='CANDIDATE_D0_CHECKS_AND_PREWATCH_OWNER_ONLY; NOT_FORMAL_ORACLE')
