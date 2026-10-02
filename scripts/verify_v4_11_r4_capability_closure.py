"""R3 to R4 business diffs and exhaustive residual input attribution."""
from scripts.next_round_execution_r4 import *
from collections import Counter
import gzip,json

OUT='reports/v4_11_r4/'
def gz(ref):return json.loads(gzip.decompress(exact(ref).read_bytes()))

def category(reason,field=None):
    if field and field.startswith('rps') or 'RPS' in reason or 'UNIVERSE_MEMBER' in reason:return 'ACCEPTED_RPS_UNAVAILABLE'
    if 'EPISODE' in reason:return 'PRIOR_EPISODE_UNAVAILABLE'
    if 'LOO' in reason:return 'SAME_DAY_LOO_NOT_FORMALLY_ADMITTED'
    if 'SUSPEN' in reason:return 'CONFIRMED_SUSPENSION'
    if 'ADJUSTMENT' in reason:return 'ACCEPTED_ADJUSTMENT_UNSUPPORTED_OR_INCOMPATIBLE'
    if 'GAP' in reason:return 'UNEXPLAINED_DATA_GAP'
    if 'HISTORY' in reason:return 'INSUFFICIENT_HISTORY'
    if 'DENOMINATOR' in reason or 'ATR' in reason:return 'EXPLICIT_ACCEPTED_MATHEMATICAL_CAPABILITY_LIMITATION'
    return 'OTHER_EXPLICIT_ACCEPTED_CAPABILITY_LIMITATION'

def close(summaryref,d2ref,eventref):
    summary=read(summaryref['path']);d2=read(d2ref['path']);er=read(eventref['path'])
    seal=read('reports/v4_11_r4a/R4A_SEALED_PRODUCER_SET.json')
    oldseal=read('reports/v4_11_r3a/R3A_SEALED_PRODUCER_SET_R2.json')
    oldsummary=read('reports/v4_11_r3/V4_11_R3_FULL_MARKET_SUMMARY.json');oldd2=read('reports/v4_11_r3/V4_11_R3_D2_READBACK.json');older=read('reports/v4_11_r3/V4_11_R3_EVENT_REPLAY.json')
    fielddiff={};inputunknown=[];stale=[];facts_by_id={}
    for day in seal['publications']:
        old={r['security_id']:r for r in gz(oldseal['publications'][day])['rows']};new=gz(seal['publications'][day])['rows'];transitions=Counter();reasons_before=Counter();reasons_after=Counter()
        if day=='2026-09-30':facts_by_id={r['security_id']:r for r in new}
        for r in new:
            for f,fact in r['facts'].items():
                prior=old[r['security_id']]['facts'][f]
                if (prior['value'],prior['quality'],prior['reason'])!=(fact['value'],fact['quality'],fact['reason']):transitions[f+':'+prior['quality']+'->'+fact['quality']]+=1
                if prior['quality']=='UNKNOWN':reasons_before[prior['reason']]+=1
                if fact['quality']=='UNKNOWN':
                    reasons_after[fact['reason']]+=1
                    if fact['reason'] in ('MISSING_OR_MIXED_COORDINATE_MASTER_SESSION','TARGET_AFFINE_IDENTITY_MUST_MATCH_EVERY_PRICE_SLOT'):raise ValueError('COEFFICIENT_GATE_REASON_FORBIDDEN')
                    inputunknown.append(dict(trade_date=day,security_id=r['security_id'],field=f,reason=fact['reason'],category=category(fact['reason'],f),source_window_identity=fact['window_identity']))
        fielddiff[day]=dict(transitions=dict(transitions),unknown_reasons_before=dict(reasons_before),unknown_reasons_after=dict(reasons_after),explanation='Changed coefficient-only exclusions admitted using accepted basis/revision; target/stated historical suspension, missing raw master slots, adjustment support, accepted RPS and explicit diagnostic limits remain. No missing-to-FALSE change; legacy thresholds unchanged.')
    derivationref=next(r for r in read(d2['contract']['path'])['allowed_source_bindings'] if 'D2_TARGET_UPSTREAM_DERIVATIONS_2026-09-30' in r['path'])
    derivations={r['security_id']:r['evidence'] for r in gz(derivationref)}
    for r in gz(d2['current'])['rows']:
        if r['state_freshness']!='STALE':continue
        unknown=[dict(field=f,reason='REQUIRED_INPUT_UNKNOWN',producer=x['producer_contract_id'],publication=x['publication_id']) for f,x in r['input_provenance'].items() if x['required'] and x['quality']=='UNKNOWN' and x['status']!='NOT_APPLICABLE' and (f!='frozen_invalidation' or bool(r['episode_id']))]
        if not unknown and 'SUSPENSION' in r['unknown_predicates']:unknown=[dict(field='suspended',reason='CONFIRMED_SUSPENSION',producer=r['input_provenance']['suspended']['producer_contract_id'])]
        if not unknown:raise ValueError('STALE_WITHOUT_EXPLICIT_REQUIRED_INPUT:'+r['entity_id'])
        if any(x.get('publication') is None and x['field'] not in ('episode_invalidation_contract_id','frozen_invalidation') for x in unknown):raise ValueError('IMPLEMENTED_REQUIRED_PRODUCER_WIRING_MISSING')
        roots=[];evidence=derivations[r['entity_id']]
        for field,fact in facts_by_id[r['entity_id']]['facts'].items():
            if fact['quality']=='UNKNOWN':roots.append(dict(owner='D0_TARGET_FACT',field=field,reason=fact['reason']))
        for owner in ('core_factors','primitives','seed_facts'):
            for field,fact in evidence[owner].items():
                if fact.get('value') is None and field!='pos250':roots.append(dict(owner=owner,field=field,reason=fact.get('unknown_reason',fact.get('reason'))))
        if any(x['field'] in ('frozen_invalidation','episode_invalidation_contract_id') for x in unknown):roots.append(dict(owner='FROZEN_EPISODE',reason='V4_12_INVALIDATION_NOT_AUTHORIZED'))
        if not roots and unknown[0]['reason']!='CONFIRMED_SUSPENSION':raise ValueError('STALE_WITHOUT_SOURCE_ROOT_CAUSE')
        stale.append(dict(entity_id=r['entity_id'],required_unknown=unknown,source_root_causes=roots,derivation_source=derivationref,reducer_unknown_predicates=r['unknown_predicates'],frozen_invalidation_role='V4-12 not authorized; prior-episode consumer unavailable where episode active'))
    attribution=write(OUT+'RESIDUAL_UNKNOWN_ATTRIBUTION.json',dict(status='PASS',target_unknown_facts=inputunknown,categories=dict(Counter(r['category'] for r in inputunknown)),D2_stale_rows=stale,stale_count=len(stale),stale_producer_wiring_missing=0,banned_coefficient_generic_reasons=0,permissions=PERMISSIONS))
    d0old={r['security_id']:r for r in gz(oldsummary['D0']['2026-09-30'])['rows']};d0new=gz(summary['D0']['2026-09-30'])['rows']
    diff=write(OUT+'R3_TO_R4_BUSINESS_DIFF.json',dict(status='PASS_CONTRACT_CORRECTNESS_NOT_UNKNOWN_MINIMIZATION',facts=fielddiff,D0_transition_counts=dict(Counter(d0old[r['security_id']]['confirmation_status']+'->'+r['confirmation_status'] for r in d0new)),D2=dict(before={k:oldd2[k] for k in ('maturity_counts','final_eligibility_counts','state_freshness_counts')},after={k:d2[k] for k in ('maturity_counts','final_eligibility_counts','state_freshness_counts')}),Event=dict(before=older['event_counts'],after=er['event_counts']),additional_source_window_correction='R3 serialized only 27 slots to D2 although accepted Core requires MA60, prior60 and slope60+10; R4 passes the complete 129/130 source window already used by legacy features. No producer date relabel or invented fact.',residual=attribution))
    candidate=write(OUT+'V4_11_ACCEPTANCE_CANDIDATE.json',dict(status='V4_11_R4_REAL_DAG_CANDIDATE_READY_FOR_EXTERNAL_REAUDIT',artifact_role='V4_11_ACCEPTANCE_CANDIDATE',formal_accepted_head=False,confirmation_LAUNCH_RECOVERY='FORMAL_CANDIDATE',Pullback_Trend='DIAGNOSTIC_ONLY',D2_bridge='ENGINEERING_CANDIDATE',Event_engine='ENGINEERING_CANDIDATE',event_evidence='RECONSTRUCTED_LEFT_CENSORED',knowledge_lineage='RECONSTRUCTED_CORRECTED',AS_RECORDED=False,summary=summaryref,D2_readback=d2ref,event_replay=eventref,residual_attribution=attribution,business_diff=diff,permissions=PERMISSIONS,accepted=False,StageHead='KEEP_V4_00_TO_V4_10_ACCEPTED',DataHead='KEEP_2026-09-30',next_stage='CLEAN_CHECKOUT_COMMIT_PUSH_STOP_EXTERNAL_REAUDIT'))
    print('R4_CAPABILITY_CLOSURE_COMPLETE')
    return candidate
