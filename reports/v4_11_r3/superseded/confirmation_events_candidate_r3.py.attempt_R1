"""Frozen STATE_EVENT_V1 predicate extraction for real, explicit candidates."""
import ast
from copy import deepcopy
from functools import lru_cache
from .confirmation import digest,package,ConfirmationError
from .confirmation_d2_candidate_r3 import verify_candidate_d2_publication,validate_candidate_output
from . import confirmation_events

EVENT_QUALITY_CONTRACT='V4_11_R3C_EVENT_PUBLICATION_QUALITY_V1'

def event_unknown_reasons(current,prior):
    """Admission quality only; the exact raw STATE_EVENT_V1 AST is unchanged.

    A stale predecessor is evidence of an unknown transition, never evidence
    that the stock was previously unconfirmed. A genuinely absent entity can
    still produce FIRST_OBSERVED from a fresh current state.
    """
    reasons=[]
    for role,state in (('CURRENT',current),('PRIOR',prior)):
        if state is None:
            continue
        if (state.get('state_freshness')!='FRESH'
                or state.get('validity') not in ('VALID','INVALIDATED')
                or state.get('final_eligibility') not in ('TRUE','FALSE')
                or state.get('maturity') not in ('NONE','SEED','PREWATCH','WARM','CONFIRMED')):
            reasons.append('UNKNOWN_'+role+'_D2_REQUIRED_FACTS')
    # Scenario transition predicates compare both endpoints only when both
    # are active confirmations. Missing optional health alone does not change
    # whether an endpoint was confirmed.
    def active(state):
        return bool(state and state.get('maturity')=='CONFIRMED'
            and state.get('final_eligibility')=='TRUE' and state.get('validity')=='VALID')
    if active(current) and active(prior):
        for role,state in (('CURRENT',current),('PRIOR',prior)):
            if state.get('scenario_status')!='KNOWN':
                reasons.append('UNKNOWN_'+role+'_D2_SCENARIO')
    return reasons

def freeze(*,target_date,prior_date,calendar_publication_id,rows,source_binding,scope,calendar_manifest,episode_history=None):
    if scope!='REAL_SEALED_CANDIDATE_REPLAY_ONLY':raise ConfirmationError('REAL_CANDIDATE_PRIOR_REQUIRED')
    dates=[s['trade_date'] for s in calendar_manifest['sessions']]
    if target_date not in dates or dates.index(target_date)==0 or dates[dates.index(target_date)-1]!=prior_date:raise ConfirmationError('EXACT_PREVIOUS_CALENDAR_SESSION_REQUIRED')
    if prior_date>=target_date:raise ConfirmationError('SAME_DAY_REVISION_PARENT_FORBIDDEN')
    if rows!=verify_candidate_d2_publication(source_binding):raise ConfirmationError('PRIOR_D2_EXACT_REEXECUTION_REQUIRED')
    if any(r['trade_date']!=prior_date or r['calendar_publication_id']!=calendar_publication_id for r in rows):raise ConfirmationError('PRIOR_SESSION_IDENTITY_MISMATCH')
    frozen=dict(contract_id='V4_11_R3_FROZEN_PRIOR_CANDIDATE',target_trade_date=target_date,prior_trade_date=prior_date,
        calendar_publication_id=calendar_publication_id,rows=rows,source_binding=source_binding,scope=scope,calendar_manifest=calendar_manifest,episode_history=episode_history or [])
    return dict(frozen,head_digest=digest(frozen))

@lru_cache(maxsize=1)
def runtime():
    path=confirmation_events.__file__
    node=next(n for n in ast.parse(open(path,encoding='utf8').read()).body if isinstance(n,ast.FunctionDef) and n.name=='state_events')
    node=deepcopy(node)
    # Only the bridge's verifier import changes; all event predicates and the
    # previous-session invariant remain the exact frozen source AST.
    node.body=[n for n in node.body if not isinstance(n,ast.ImportFrom)]
    g=dict(confirmation_events.__dict__,validate_output=validate_candidate_output,freeze_prior_session=freeze,verify_d2_publication=verify_candidate_d2_publication)
    exec(compile(ast.fix_missing_locations(ast.Module(body=[node],type_ignores=[])),'<R3_candidate_exact_STATE_EVENT_V1>','exec'),g)
    return g['state_events']

def events(publication,frozen,*,revision_of=None):
    result=runtime()(publication,frozen,revision_of=revision_of)
    states={r['entity_id']:r for r in publication['rows']}
    prior_states={r['entity_id']:r for r in frozen['rows']}
    for row in result:
        reasons=event_unknown_reasons(states[row['entity_id']],prior_states.get(row['entity_id']))
        known=not reasons
        row.update(scope='REAL_DAG_CANDIDATE_ONLY',accepted=False,AS_RECORDED=False,
            event_quality='KNOWN' if known else reasons[0],event_unknown_predicates=reasons,
            event_quality_contract_id=EVENT_QUALITY_CONTRACT,
            effective_event=row['primary_event'] if known else 'UNKNOWN',knowledge_lineage='RECONSTRUCTED_CORRECTED')
        row['permissions']=dict(row['permissions'],global_mandatory_adoption=False)
    return result
