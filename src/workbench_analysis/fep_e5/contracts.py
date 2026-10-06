"""Versioned exact identities and closed promotion gates; no label/fit dependencies."""
from copy import deepcopy
from datetime import datetime
import math
from workbench_analysis.fep_e1.contracts import digest

VERSION='FEP_E5_PROJECTION_PRIORITY_V1'
IDENTITY=('scope_id','observation_scope','target_id','horizon','feature_contract_id')
SLOT=('namespace',*IDENTITY,'entity_id','signal_key','trade_date','model_family_scope','model_selection_cutoff','prediction_deadline')
GRANT=('scope_id','target_id','horizon','feature_contract_id','model_set_id','capability')
LAYER=('priority_bucket','emergence','structure','delta3','risk','days_since_improvement','prior20_amount')
STATES=('READY','UNKNOWN','NOT_ENABLED','NOT_APPLICABLE','REJECTED_OOD','REJECTED_QUALITY','REJECTED_SUPPORT','CONFLICTING','MISSING_MODEL','MISSED_SLOT','MISSING_DEPENDENCY')

def require(condition,reason):
    if not condition:raise ValueError('E5_'+reason)
def utc(value):
    dt=datetime.fromisoformat(value.replace('Z','+00:00'));require(dt.tzinfo is not None and dt.utcoffset().total_seconds()==0,'UTC_REQUIRED');return dt
def logical(payload):
    return digest({k:v for k,v in payload.items() if k not in ('created_at','accepted_at','recorded_at','started_at','finished_at','frozen_at','run_id','logical_digest')})
def exact(a,b,kind):require(digest(a)==digest(b),kind+'_MUTATION')
def slot_identity(slot):
    require(all(slot.get(k) is not None for k in SLOT),'SLOT_IDENTITY_INCOMPLETE')
    require(utc(slot['model_selection_cutoff'])<=utc(slot['prediction_deadline']),'SLOT_CLOCK_ORDER')
    require(slot['namespace'].startswith('FEP_E5_'),'NAMESPACE_REQUIRED')
    return digest({k:slot[k] for k in SLOT})
def compatible(slot,model):
    for key in IDENTITY:require(slot[key]==model[key],'SCOPE_TARGET_HORIZON_FEATURE_MISMATCH:'+key)
    require(slot['namespace']==model['namespace'] and slot['model_family_scope']==model['model_family'],'MODEL_NAMESPACE_MISMATCH')
    require(model.get('champion') is False,'CHAMPION_FORBIDDEN')
    require(utc(model['activation_effective_at'])<=utc(slot['model_selection_cutoff']),'LATE_MODEL_ACTIVATION')
def evidence(payload):
    require(payload.get('prediction_evidence') in ('HISTORICAL_SIMULATION','ENGINEERING_FIXTURE','CORRECTED_RECONSTRUCTION'),'FIRST_OBSERVED_OR_REAL_OOS_FORBIDDEN')
    require(payload.get('FIRST_OBSERVED') is False and payload.get('REAL_OOS') is False,'REAL_EVIDENCE_FORBIDDEN')
    require(payload.get('PROMOTION_EVIDENCE') is False,'SEEN_PROMOTION_FORBIDDEN')
def resources(operations):
    require(operations.get('new_model_training',0)==0,'MODEL_TRAINING_FORBIDDEN')
    require(operations.get('new_label_resolution',0)==0,'LABEL_RESOLUTION_FORBIDDEN')
def snapshot_input(row):
    require(row.get('input_mode')=='EXACT_IMMUTABLE_SNAPSHOT','CURRENT_HEAD_REBUILD_FORBIDDEN')
    require(row.get('snapshot_id') and row.get('snapshot_digest') and row.get('observation_id'),'MISSING_DEPENDENCY')
    require(logical(row['snapshot'])==row['snapshot_digest'],'SNAPSHOT_DIGEST_MISMATCH')
    require(row['snapshot']['observation_id']==row['observation_id'],'SNAPSHOT_OBSERVATION_MISMATCH')
    # Only explicitly projected features enter input identity. No label/outcome fields are admitted.
    require(not ({'outcome','label','label_revision','forward_return'} & set(row['snapshot'])),'LABEL_INPUT_FORBIDDEN')
    return logical(dict(observation_id=row['observation_id'],snapshot_id=row['snapshot_id'],snapshot_digest=row['snapshot_digest']))
def permission_key(model,capability):return {k:(capability if k=='capability' else model[k]) for k in GRANT}
def permission_request(model,capability):
    require(capability=='SHADOW_INFERENCE','DISPLAY_PRIORITY_PRODUCTION_PERMISSION_CLOSED')
    require(model.get('champion') is False,'CHAMPION_FORBIDDEN')
    return permission_key(model,capability)
def future_evaluation(stub):
    require(stub.get('status')=='NOT_ACTIVE' and stub.get('evaluation_open') is False,'FUTURE_OOS_CLOSED')
    require(all(v!='UNSET' for v in stub.get('dimensions',{}).values()),'FUTURE_OOS_UNSET')
    raise ValueError('E5_SEPARATE_OOS_TASK_REQUIRED')
def classify(axes,conditions,thresholds):
    if not all(conditions.values()):return 'UNKNOWN'
    if not thresholds or any(thresholds.get(k) is None for k in ('statistic','positive','negative','risk_limit')):return 'NOT_FROZEN'
    value=axes.get(thresholds['statistic']);risk=axes.get('risk_expectancy')
    if value is None or risk is None:return 'UNKNOWN'
    if value>thresholds['positive'] and risk>thresholds['risk_limit']:return 'CONFLICTING'
    if value>thresholds['positive']:return 'POSITIVE'
    if value<thresholds['negative']:return 'NEGATIVE'
    return 'NEUTRAL'
def status(quality,support,ood,model_available=True,missed=False):
    if missed:return 'MISSED_SLOT'
    if not model_available:return 'MISSING_MODEL'
    if quality!='OBSERVED':return 'REJECTED_QUALITY'
    if support!='SUPPORTED':return 'REJECTED_SUPPORT'
    if ood.get('hard_reasons'):return 'REJECTED_OOD'
    return 'READY'
def protocol_guard(actual,frozen):
    exact(actual,frozen,'PROTOCOL')
    require(actual['E5_EFFECTIVENESS_EVALUATION']=='CLOSED_ENGINEERING_ONLY','EFFECTIVENESS_EVALUATION_CLOSED')
def engineering_disposition(checks):
    required=('contract','protected','entry_ledger_api_rollback','daily_fail_closed')
    require(set(checks)==set(required),'DISPOSITION_CHECKS_INCOMPLETE')
    return 'PASS_ENGINEERING_ONLY_NO_PROMOTION' if all(checks.values()) else 'BLOCKED'

def daily_projection(pool,predictions,trade_date,protocol,*,synthetic_only=False,tie_break_enabled=False,risk_events=()):
    require(protocol['layer_keys']==list(LAYER),'POST_RESULT_PRIORITY_TUPLE')
    require(protocol['fep_tuple']==['return_expectancy_desc','stable_entity_id'],'POST_RESULT_PRIORITY_TUPLE')
    require(len({r['entity_id'] for r in pool})==len(pool),'DUPLICATE_CANDIDATE')
    require(all(r['trade_date']==trade_date for r in pool),'CANDIDATE_DAY_MISMATCH')
    if tie_break_enabled:require(synthetic_only,'REAL_DAILY_PRIORITY_NOT_ENABLED')
    original=deepcopy(pool);rows=[];covered=0;counts=dict(rejected_OOD=0,missing_prediction=0,missing_model=0,missing_daily_observation=0)
    for candidate in pool:
        pred=predictions.get(candidate['entity_id']);reason=None
        if not synthetic_only:reason='NOT_ENABLED_NO_ACCEPTED_DAILY_SCOPE';counts['missing_daily_observation']+=int(candidate['eligible'])
        elif pred is None:reason='MISSING_PREDICTION';counts['missing_prediction']+=int(candidate['eligible'])
        else:
            require(pred['observation_scope']=='DAILY_LANDMARK' and pred['scope_id']=='FEP_STOCK_DAILY_CORE','ENTRY_DAILY_REUSE')
            require(pred['trade_date']==pred['snapshot_trade_date']==pred['slot_trade_date']==pred['accepted_trade_date']==trade_date,'STALE_ENTRY_OR_DAILY_FORECAST')
            evidence(pred);require(pred['synthetic_only'] is True,'SYNTHETIC_EVIDENCE_MISMATCH')
            if not pred.get('model_id'):reason='MISSING_MODEL';counts['missing_model']+=int(candidate['eligible'])
            elif pred['quality_state']!='OBSERVED':reason='REJECTED_QUALITY'
            elif pred['support_state']!='SUPPORTED':reason='REJECTED_SUPPORT'
            elif pred['OOD_state']!='PASS_FIXTURE':reason='REJECTED_OOD';counts['rejected_OOD']+=int(candidate['eligible'])
            elif pred['axes'].get('return_expectancy') is None:reason='UNKNOWN'
            else:covered+=int(candidate['eligible'])
        rows.append(dict(entity_id=candidate['entity_id'],v1_rank=candidate['priority_rank'],v1_display_rank=candidate['display_rank'],
            v2_shadow_rank=candidate['priority_rank'],projection_state=reason or 'READY',action='ABSTAIN' if reason else 'ENGINEERING_SHADOW',
            axes=deepcopy(pred['axes']) if pred is not None and reason is None else None,eligible=candidate['eligible'],
            v1_identity=logical(candidate),layer_identity=digest([candidate[k] for k in LAYER]),risk=deepcopy(candidate.get('risk_events',[]))))
    if tie_break_enabled:
        # Keep every rejected position. FEP only permutes covered rows within an exact V1 layer.
        layers={}
        for i,row in enumerate(rows):
            if row['projection_state']=='READY' and row['eligible']:layers.setdefault(row['layer_identity'],[]).append(i)
        for indexes in layers.values():
            ranks=sorted(rows[i]['v1_rank'] for i in indexes)
            ordered=sorted(indexes,key=lambda i:(-rows[i]['axes']['return_expectancy'],rows[i]['entity_id']))
            for rank,index in zip(ranks,ordered):rows[index]['v2_shadow_rank']=rank
    exact(pool,original,'PRIORITY_V1')
    eligible=sum(r['eligible'] for r in pool)
    return dict(contract_id='PRIORITY_V2_SHADOW_E5_V1',rows=rows,full_pool_digest=logical(dict(pool=pool)),eligible_candidates=eligible,
        covered_candidates=covered,coverage_ratio=covered/eligible if eligible else 0.0,**counts,risk_events=deepcopy(list(risk_events)),
        same_K=protocol['K'],same_candidate_set=True,synthetic_only=synthetic_only,REAL_OOS=False,FIRST_OBSERVED=False,
        REAL_PRIORITY_SHADOW='NOT_GRANTED',v2_active=False,default_tie_break_enabled=False,
        status='PASS_ENGINEERING_FIXTURE' if synthetic_only else 'NOT_ENABLED_NO_ACCEPTED_DAILY_SCOPE')
def verify_shadow(pool,shadow,risk_events):
    require(len(shadow['rows'])==len(pool) and {r['entity_id'] for r in shadow['rows']}=={r['entity_id'] for r in pool},'DENOMINATOR_DROP')
    by_id={r['entity_id']:r for r in pool}
    for row in shadow['rows']:
        source=by_id[row['entity_id']];require(row['v1_identity']==logical(source) and row['v1_rank']==source['priority_rank'] and row['eligible']==source['eligible'],'PRIORITY_V1_OR_ELIGIBILITY_MUTATION')
        exact(row['risk'],source.get('risk_events',[]),'RISK_EVENT')
    exact(shadow['risk_events'],list(risk_events),'RISK_EVENT')
    require(shadow['v2_active'] is False,'REAL_DAILY_API_ACTIVE')
def write_target(namespace):require(namespace=='fep_e5_engineering','CORE_PROFILE_STATE_COHORT_WRITE_FORBIDDEN')
