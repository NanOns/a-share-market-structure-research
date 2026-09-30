"""RESEARCH_STATE_V1 D2 interface. No D0/D1 detector implementation or live DAG."""
from copy import deepcopy
import hashlib
import json
import math
from datetime import date
from pathlib import Path
from .state_identity import digest, INTERFACE, CANONICALIZATION
from .state_provenance import validate_inputs, validate_output

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = 'RESEARCH_STATE_V1'
PARAMETERS = 'V4_10_STATE_REDUCER_PARAMETER_SET_V1'
TRI = {'TRUE', 'FALSE', 'UNKNOWN'}

def load_package():
    freeze=json.loads((ROOT/'reports/v4_10/V4_10_R1_1_CONTRACT_FREEZE.json').read_text(encoding='utf8'))
    if freeze['status']!='PASS_R1_1_LINEAGE_INTERFACE_FREEZE' or freeze['contract_id']!='V4_10_R1_1_CONTRACT_FREEZE':
        raise ValueError('STATE_FREEZE_IDENTITY_MISMATCH')
    for binding in freeze['bindings'].values():
        if hashlib.sha256((ROOT/binding['path']).read_bytes()).hexdigest()!=binding['sha256']:
            raise ValueError('STATE_FREEZE_BINDING_MISMATCH')
    def read(name):
        return json.loads((ROOT/('config/v4_10_'+name+'_r1_1.json')).read_text(encoding='utf8'))
    c, a, p = read('research_state_contract'), read('machine_ast'), read('parameter_set')
    if c['contract_id']!=CONTRACT or p['parameter_set_id']!=PARAMETERS or a['rule_order']!=c['rule_order']:
        raise ValueError('STATE_CONTRACT_IDENTITY_MISMATCH')
    if a['rule_order']!=['R1_MODEL_BOUNDARY','R2_HARD_INVALIDATION','R3_REQUIRED_UNKNOWN','R4_STAGE_SELECTION',
                         'R5_HYSTERESIS','R6_HEALTH','R7_TRACKING','R8_EXPIRY','R9_REENTRY']:
        raise ValueError('STATE_RULE_ORDER_MISMATCH')
    if any(p[k]!=v for k,v in dict(downgrade_sessions=2,expiry_sessions=10,expiry_improvement_pp=3,health_deadband_pp=3).items()):
        raise ValueError('UNAUTHORIZED_BUSINESS_PARAMETER_CHANGE')
    return c, a, p

def _fact(value, field, unknown):
    if value not in TRI: raise ValueError('INVALID_TRI_STATE:'+field)
    if value=='UNKNOWN': unknown.append(field)
    return value

def reduce_state(inputs, *, ledger=None):
    """Reduce explicit publication facts; synthetic positives require declared fixture mode.

    session_index is a monotone index from the caller's bound market calendar, never
    calendar-day subtraction. prior_state_binding freezes the whole previous payload.
    """
    c, ast, p = load_package()
    x=validate_inputs(inputs,ledger); required=c['input_required_fields']
    if set(required)-set(x): raise ValueError('MISSING_STATE_INPUT_FIELDS')
    if x['entity_type'] not in ('STOCK','SECTOR') or x['mode'] not in ('SYNTHETIC_CONTRACT_VECTOR','ACCEPTED_FACT_INTERFACE'):
        raise ValueError('STATE_INPUT_SCOPE_INVALID')
    if not isinstance(x['session_index'],int) or isinstance(x['session_index'],bool) or x['session_index']<0:
        raise ValueError('INVALID_MARKET_SESSION_INDEX')
    date.fromisoformat(x['trade_date'])
    if not x['entity_id'] or not x['calendar_publication_id'] or not x['input_publication_ids']:
        raise ValueError('EXPLICIT_INPUT_PUBLICATION_LINEAGE_REQUIRED')
    if x['suspended'] not in TRI or x['followup_complete'] not in TRI or type(x['model_boundary']) is not bool:
        raise ValueError('STATE_BOOLEAN_INTERFACE_INVALID')
    prior=x['prior_state']; boundary=x['model_boundary']; previous=prior
    if prior:
        if prior['entity_id']!=x['entity_id'] or prior['entity_type']!=x['entity_type'] or prior['session_index']>x['session_index']:
            raise ValueError('ILLEGAL_PRIOR_STATE_LINEAGE')
        if (prior['model_contract_id']!=CONTRACT or prior['parameter_set_id']!=PARAMETERS) and not boundary:
            raise ValueError('MODEL_BOUNDARY_REQUIRED')
        if prior['entity_type']=='STOCK' and prior['maturity']=='WARM' and not boundary:
            raise ValueError('ILLEGAL_STOCK_WARM_PRIOR')
        for axis, domain in c['axes'].items():
            allowed=domain[x['entity_type']] if isinstance(domain,dict) else domain
            if prior[axis] not in allowed:
                raise ValueError('ILLEGAL_PRIOR_AXIS:'+axis)
    elif x['prior_state_binding'] is not None:
        raise ValueError('ORPHAN_PRIOR_STATE_BINDING')
    if boundary: prior=None  # old episode remains in separate immutable publication
    reasons=['MODEL_BOUNDARY'] if boundary else []
    unknown=list(x['provenance_unknown']); matched=[]; fact_values={}; statuses={}
    for stage in ast['stage_precedence']:
        f=x['detectors'][stage]
        statuses[stage]=f['status']
        if stage=='WARM' and x['entity_type']=='STOCK':
            if f['status']!='NOT_APPLICABLE' or f['value']!='UNKNOWN': raise ValueError('STOCK_WARM_NOT_APPLICABLE_REQUIRED')
            continue
        if f['status'] not in ('IMPLEMENTED','SYNTHETIC','NOT_IMPLEMENTED','NOT_APPLICABLE'):
            raise ValueError('DETECTOR_STATUS_INVALID')
        value=_fact(f['value'],stage,unknown)
        if f['status']=='NOT_APPLICABLE':
            if value!='UNKNOWN': raise ValueError('UNAVAILABLE_DETECTOR_MUST_BE_UNKNOWN')
            unknown.remove(stage); continue
        if f['status']=='NOT_IMPLEMENTED' and value!='UNKNOWN':
            raise ValueError('UNIMPLEMENTED_DETECTOR_MUST_BE_UNKNOWN')
        if f['status']=='SYNTHETIC' and x['mode']!='SYNTHETIC_CONTRACT_VECTOR':
            raise ValueError('SYNTHETIC_DETECTOR_IN_ACCEPTED_INPUT')
        if x['mode']=='ACCEPTED_FACT_INTERFACE' and stage in ('CONFIRMED','WARM') and f['status']!='NOT_IMPLEMENTED':
            raise ValueError('UNACCEPTED_D0_D1_DETECTOR')
        expected=c['producer_contracts'].get(stage)
        if f['status']=='IMPLEMENTED' and (not expected or f['contract_id']!=expected or f['parameter_set_id']!=c['producer_parameters'].get(stage) or
                f['publication_id'] not in x['input_publication_ids']):
            value='UNKNOWN'; unknown.append(stage+':PRODUCER_LINEAGE_MISMATCH')
        fact_values[stage]=value
        if value=='TRUE': matched.append(stage)
    damage=_fact(x['core_price_damage'],'core_price_damage',unknown)
    invalid=x['frozen_invalidation']
    invalid_required=bool(prior and prior['episode_id'])
    invalid_value=_fact(invalid['value'],'frozen_invalidation',unknown if invalid_required else [])
    _fact(x['suspended'],'suspended',unknown)
    if invalid_value=='TRUE' and (not prior or not prior['episode_id'] or invalid['episode_id']!=prior['episode_id'] or
            not invalid['contract_id'] or invalid['contract_id']!=prior.get('invalidation_contract_id')):
        invalid_value='UNKNOWN'; unknown.append('invalidation:EPISODE_CONTRACT_MISMATCH')
    metric=x['delta3'] if x['entity_type']=='STOCK' else x['dq5']
    if metric is not None and (not isinstance(metric,(float,int)) or isinstance(metric,bool) or not math.isfinite(metric)):
        raise ValueError('FINITE_HEALTH_METRIC_REQUIRED')
    if x['risk'] not in c['risk_domain']: raise ValueError('INVALID_RISK')
    old_stage=prior['maturity'] if prior else 'NONE'
    episode=prior['episode_id'] if prior else None
    result=dict(entity_id=x['entity_id'], entity_type=x['entity_type'], trade_date=x['trade_date'], session_index=x['session_index'],
        calendar_publication_id=x['calendar_publication_id'], mode=x['mode'], model_contract_id=CONTRACT,parameter_set_id=PARAMETERS,
        cutoff=x['cutoff'],
        interface_contract_id=INTERFACE,canonicalization_contract_id=CANONICALIZATION,calendar_binding=x['calendar_binding'],
        input_provenance=x['input_provenance'],input_publication_manifest_digest=x['input_publication_manifest_digest'],
        prior_state_binding=x['prior_state_binding'],input_publication_ids=x['input_publication_ids'],input_digest=digest(x),
        maturity=old_stage,health='UNKNOWN',validity='UNKNOWN',tracking=prior['tracking'] if prior else 'CLOSED',
        scenario=prior['scenario'] if prior else 'NONE',scenario_status='UNKNOWN',state_freshness='STALE',
        final_eligibility='UNKNOWN',raw_qualification=dict(fact_values),detector_statuses=statuses,
        episode_id=episode,parent_episode_id=prior.get('parent_episode_id') if prior else None,
        invalidation_contract_id=prior.get('invalidation_contract_id') if prior else None,
        downgrade_candidate=None,downgrade_count=0,expiry_count=prior.get('expiry_count',0) if prior else 0,
        improvement_baseline=prior.get('improvement_baseline') if prior else None,
        market_age=(prior.get('market_age',0)+x['session_index']-prior['session_index']) if prior else 0,
        exit_session_index=prior.get('exit_session_index') if prior else None,
        matched_predicates=matched,unknown_predicates=unknown,transition_reasons=reasons,
        boundary_event=dict(kind='MODEL_BOUNDARY',previous_episode_id=previous['episode_id'] if previous else None,
            authorized_manifest=x['authorized_boundary']) if boundary else None,
        preserved_followup_episode_ids=([previous['episode_id']] if boundary and previous and previous['episode_id'] else
            list(prior.get('preserved_followup_episode_ids',[])) if prior else []))
    def finish():
        for field,fact in x['input_provenance'].items():
            if not fact['required'] and fact['quality']=='UNKNOWN':
                reason=field+':OPTIONAL_INPUT_UNKNOWN'
                if reason not in unknown:unknown.append(reason)
        result['publication_id']='V4_10:'+digest(result)
        validate_output(result)
        return result
    if episode and (damage=='TRUE' or invalid_value=='TRUE'):
        result.update(maturity='NONE',health='DAMAGED',validity='INVALIDATED',final_eligibility='FALSE',tracking='FOLLOWUP',
            state_freshness='FRESH',exit_session_index=x['session_index'])
        reasons.append('HARD_INVALIDATION'); return finish()
    if unknown or x['suspended']=='TRUE':
        if x['suspended']=='TRUE': unknown.append('SUSPENSION')
        reasons.append('REQUIRED_FACTS_UNKNOWN_PRESERVE'); return finish()
    stage=next((s for s in ast['stage_precedence'] if fact_values.get(s)=='TRUE'),'NONE')
    result.update(validity='VALID',state_freshness='FRESH',final_eligibility='TRUE' if stage!='NONE' else 'FALSE')
    rank={s:i for i,s in enumerate(['NONE','SEED','PREWATCH','WARM','CONFIRMED'])}
    if rank[stage]<rank[old_stage]:
        count=1
        if prior and prior.get('downgrade_candidate')==stage:
            if x['session_index']==prior['session_index']+1: count=prior.get('downgrade_count',0)+1
            elif x['session_index']==prior['session_index']: count=prior.get('downgrade_count',0)
        result.update(downgrade_candidate=stage,downgrade_count=count)
        if count<p['downgrade_sessions']: stage=old_stage; reasons.append('DOWNGRADE_HOLD')
        else: reasons.append('DOWNGRADE_APPLIED')
    elif rank[stage]>rank[old_stage]: reasons.append('UPGRADE_IMMEDIATE')
    result['maturity']=stage
    if x['risk']=='EXTREME': result['health']='EXHAUSTED'
    elif metric is None or x['risk']=='UNKNOWN':
        unknown.append('HEALTH_HISTORY_OR_RISK_UNKNOWN')
    else:
        result['health']='WEAKENING' if metric < -p['health_deadband_pp'] else 'IMPROVING' if metric > p['health_deadband_pp'] else 'STABLE'
    if stage in ('SEED','PREWATCH') and result['final_eligibility']=='TRUE':
        baseline=result['improvement_baseline']
        upgraded=rank[stage]>rank[old_stage]
        improved=metric is not None and baseline is not None and metric-baseline>=p['expiry_improvement_pp']
        if upgraded or improved or baseline is None:
            result.update(expiry_count=1,improvement_baseline=metric)
        elif not prior or x['session_index']>prior['session_index']:
            result['expiry_count']+=1
        if metric is None:
            result['expiry_count']=prior.get('expiry_count',0) if prior else 0
            unknown.append('EXPIRY_IMPROVEMENT_HISTORY_UNKNOWN')
        if result['expiry_count']>=p['expiry_sessions']:
            result.update(maturity='NONE',final_eligibility='FALSE',tracking='FOLLOWUP',exit_session_index=x['session_index'])
            reasons.append('EXPIRED'); stage='NONE'
    else: result['expiry_count']=0
    if stage=='NONE':
        result['tracking']='FOLLOWUP' if episode else 'CLOSED'
        if episode and old_stage!='NONE': result['exit_session_index']=x['session_index']; reasons.append('EXITED')
        if episode and x['followup_complete']=='TRUE': result['tracking']='CLOSED'; reasons.append('FOLLOWUP_COMPLETE')
    elif result['final_eligibility']=='TRUE':
        exited=prior and prior.get('exit_session_index') is not None and prior['maturity']=='NONE'
        if exited and x['session_index']<=prior['exit_session_index']:
            result.update(maturity='NONE',final_eligibility='FALSE',tracking=prior['tracking'])
            reasons.append('SAME_SESSION_REENTRY_FORBIDDEN')
        elif not episode or exited:
            parent=episode if exited else None
            result.update(episode_id='EP:'+digest([x['entity_id'],x['entity_type'],x['session_index'],CONTRACT,PARAMETERS,x['input_publication_ids']]),
                parent_episode_id=parent,tracking='ACTIVE',exit_session_index=None,market_age=0,
                invalidation_contract_id=x['episode_invalidation_contract_id'])
            reasons.append('REENTERED' if parent else 'ENROLLED')
            if parent: result['preserved_followup_episode_ids'].append(parent)
        else: result['tracking']='ACTIVE'
    else:
        # Day-1 NONE downgrade retains maturity and tracking, but is not eligible today.
        result['tracking']=prior['tracking'] if prior else 'CLOSED'
    scenario=x['scenario']
    if scenario['status']=='KNOWN':
        if scenario['value'] not in c['axes']['scenario'][x['entity_type']]: raise ValueError('INVALID_SCENARIO_AXIS')
        result.update(scenario=scenario['value'],scenario_status='KNOWN')
    elif scenario['status']!='UNKNOWN': raise ValueError('INVALID_SCENARIO_STATUS')
    else: unknown.append('SCENARIO_UNKNOWN')
    return finish()
