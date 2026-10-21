"""Read-only, fail-closed reason attribution for candidate D0/D2 owners."""
from collections import Counter
import gzip
import json

from workbench_analysis.r43_owner_replay import checked


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
    d2_binding = candidate.get('owners', {}).get(day, {}).get('focus')
    if focus_ids and d2_binding:
        for row in _load_jsonl(root, d2_binding):
            security_id = str(row.get('security_id') or row.get('entity_id') or '')
            if security_id not in focus_ids:
                continue
            focus_d2[str(row.get('final_eligibility') or 'UNKNOWN')] += 1
            for reason in row.get('unknown_predicates') or []:
                focus_d2_reasons[str(reason)] += 1
            provenance = row.get('input_provenance') or {}
            invalidation = provenance.get('frozen_invalidation') or {}
            if invalidation.get('status') == 'NOT_IMPLEMENTED':
                focus_d2_reasons['frozen_invalidation:REQUIRED_INPUT_NOT_IMPLEMENTED'] += 1
    focus_summary = dict(focus_denominator=len(focus_ids),
        d0_mapped=sum(focus_d0.values()),d0_confirmation_status_counts=dict(sorted(focus_d0.items())),
        d0_top_reason_counts=[dict(reason=k,count=v) for k,v in focus_d0_reasons.most_common(20)],
        d2_mapped=sum(focus_d2.values()),d2_final_eligibility_counts=dict(sorted(focus_d2.items())),
        d2_top_reason_counts=[dict(reason=k,count=v) for k,v in focus_d2_reasons.most_common(20)],
        source=d2_binding)
    return dict(contract_id=CONTRACT_ID, version='1.0.0', status='READY', trade_date=day,
        total=len(rows), confirmation_status_counts=dict(sorted(overall.items())),
        scenario_status_counts=dict(sorted(scenario_states.items())),
        most_common_failed_checks=[dict(reason=k,count=v) for k,v in failed_checks.most_common(20)],
        unknown_reasons=[dict(reason=k,count=v) for k,v in unknown_reasons.most_common(20)],
        prewatch_qualification_counts=dict(sorted(prewatch_states.items())),
        prewatch_unknown_predicates=[dict(reason=k,count=v) for k,v in prewatch_unknowns.most_common(20)],
        focus_trigger_count=focus_triggers,focus_intersection=focus_summary,source=binding,
        AS_RECORDED=False,PIT_ELIGIBLE=False,eligibility_mutated=False,
        scope='CANDIDATE_D0_CHECKS_AND_PREWATCH_OWNER_ONLY; NOT_FORMAL_ORACLE')
