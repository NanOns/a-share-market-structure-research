"""Freeze contemporaneous inputs plus full State for independent source review.

This is an as-of observation candidate, never a formal State/Cohort Owner.
Historical replay and live source observation cannot silently interchange.
"""
from datetime import datetime, timezone, timedelta
from pathlib import Path
import json
from .r43_owner_replay import checked, gzrows, ref
from .v4_14_replay_io import digest, publish
from .full_state_signal_candidate_v1 import produce
from .source_capture_candidate_v1 import instant

CONTRACT='FULL_STATE_ASOF_SOURCE_CANDIDATE_V2'


def validate_cutoff(value, trade_date):
    """Reject future source/window inputs before preserving scanner predicates."""
    if isinstance(value, dict):
        for key, item in value.items():
            if key in ('max_source_date','window_end_trade_date','window_start_trade_date','window_end') and item:
                if str(item)[:10] > trade_date:raise ValueError('FUTURE_STATE_WINDOW_INPUT')
            validate_cutoff(item, trade_date)
    elif isinstance(value, list):
        for item in value:validate_cutoff(item, trade_date)


def freeze_for_review(root, *, capture_binding, candidate_binding, trade_date, research_replay=False):
    root=Path(root);capture=json.loads(checked(root,capture_binding).read_bytes())
    head=json.loads(checked(root,candidate_binding).read_bytes());owner=head['owners'][trade_date]
    now=datetime.now(timezone.utc);today=now.astimezone(timezone(timedelta(hours=8))).date().isoformat()
    if head['accepted_trade_date']!=trade_date or capture['T0']!=trade_date:
        raise ValueError('ASOF_SOURCE_DATE_MISMATCH')
    if not research_replay and (trade_date!=today or capture['evidence_class']!='CURRENT_OBSERVATION_CANDIDATE'):
        raise ValueError('NO_HISTORICAL_FIRST_CAPTURE_BACKFILL')
    calendar=json.loads(checked(root,capture['calendar']).read_bytes())
    if trade_date not in calendar['session_dates']:raise ValueError('BOUND_CALENDAR_SESSION_REQUIRED')
    if instant(capture['captured_at'])>now:raise ValueError('FUTURE_CAPTURE_CLOCK')
    for source in capture['sources']:
        checked(root,source['original_bytes'])
        if source.get('requested_at') and instant(source['requested_at'])>instant(source['received_at']):
            raise ValueError('SOURCE_TIMESTAMP_ORDER_REQUIRED')
        if instant(source['received_at'])>instant(capture['captured_at']):raise ValueError('CAPTURE_PRECEDES_INPUT_RECEIPT')
    life=json.loads(checked(root,owner['lifecycle']).read_bytes())
    snapshot=json.loads(checked(root,head['membership_snapshot']).read_bytes())
    rows=gzrows(checked(root,owner['prewatch']))
    raw=gzrows(checked(root,owner['raw']))
    core=gzrows(checked(root,owner['core']))
    gaps=list(capture['gaps'])
    from .source_scope_reconciliation_v1 import reconcile
    reconciliation_binding=reconcile(root,capture_binding=capture_binding,candidate_binding=candidate_binding,trade_date=trade_date)
    reconciliation=json.loads(checked(root,reconciliation_binding).read_bytes())
    gaps.extend(reconciliation['source_gaps'])
    if set(r['security_id'] for r in core)!=set(life['active_security_ids']):gaps.append('FULL_CORE_SCOPE_INCOMPLETE')
    for group in (raw,core,rows):
        if len({r['security_id'] for r in group})!=len(group):raise ValueError('DUPLICATE_STATE_INPUT')
    for row in raw+core+rows:
        if row['trade_date']!=trade_date:raise ValueError('STATE_INPUT_TARGET_DATE_MISMATCH')
        validate_cutoff(row,trade_date)
    if any(r.get('PIT_ELIGIBLE') is not True for r in core+rows):
        gaps.append('STRICT_STATE_WINDOWS_AND_MEMBERSHIP_NOT_ADMITTED')
    model=ref(root,root/'src/workbench_analysis/r43_focus_replay.py')
    config=ref(root,root/'config/research_attention_v3.yaml')
    implementation=ref(root,root/'src/workbench_analysis/strict_source_candidate_v2.py')
    state_implementation=ref(root,root/'src/workbench_analysis/full_state_signal_candidate_v1.py')
    document=produce(rows,universe=life['active_security_ids'],trade_date=trade_date,source_binding=owner['prewatch'],
        membership_binding=head['membership_snapshot'],model_binding=model,config_binding=config,captured_at=now.isoformat())
    if document['missing_state_count']:gaps.append('STATE_UNIVERSE_HAS_MISSING_OUTPUT')
    # Every numerical scanner input and predicate stays frozen verbatim. A later
    # corrected source cannot rewrite these values or their capture clock.
    inputs=publish(root,f"data/v4/strict_source_candidates_v2/inputs/{owner['prewatch']['sha256']}.json",
        dict(T0=trade_date,rows=[dict(security_id=r['security_id'],target_values=r['target_values'],
                                    confirmation=r['confirmation'],normal_evidence=r['normal_evidence']) for r in rows]))
    bindings={k:owner[k] for k in ('raw','core','prewatch','lifecycle')}
    document.update(contract_id=CONTRACT,source_capture=capture_binding,candidate_head=candidate_binding,
        frozen_scanner_inputs=inputs,input_bindings=bindings,calendar=capture['calendar'],
        scope_reconciliation=dict(universe_count=len(life['active_security_ids']),core_count=len(core),raw_traded_count=len(raw),
            receipt=reconciliation_binding,status=reconciliation['status']),
        evidence_class='RECONSTRUCTED_RESEARCH_ONLY' if research_replay else 'ASOF_OBSERVATION_SOURCE_CANDIDATE',
        review_readiness='HISTORICAL_RESEARCH_ONLY' if research_replay else 'SOURCE_GAPS' if gaps else 'READY_FOR_INDEPENDENT_SOURCE_REVIEW',
        source_gaps=sorted(set(gaps)),full_state_model_admission='NOT_GRANTED',
        candidate_status='SOURCE_GAPS' if gaps else 'STRICT_SOURCE_CANDIDATE_READY_FOR_REVIEW',
        first_available=capture['captured_at'] if not research_replay else None,
        captured_at=now.isoformat(),formal_consumer_enabled=False,writer_grant_required_for_capture=False,
        state_window_basis='OPERATIONAL_FROZEN_T0_INPUTS; STRICT_WINDOW_AND_MEMBER_ADMISSION_PENDING')
    document.update(implementation=implementation,state_implementation=state_implementation)
    slot=digest([trade_date,capture_binding,candidate_binding,inputs,model,config,implementation,state_implementation,research_replay])
    path=f'data/v4/strict_source_candidates_v2/{slot}/source.json'
    if (root/path).exists():
        previous=json.loads((root/path).read_bytes())
        if previous['source_capture']!=capture_binding or previous['frozen_scanner_inputs']!=inputs:
            raise ValueError('ASOF_SOURCE_SLOT_COLLISION')
        return ref(root,root/path)
    return publish(root,path,document)
