"""Synthetic ledger validation/readback only. No settlement calculations or writer."""
from copy import deepcopy
import hashlib
import json

CAPS=('STOCK_CORE','STOCK_SECTOR_DEPENDENT','SECTOR_STAGE','ROTATION','SECTOR_RISK_CHANGE')
LANES=('SHADOW_REAL','PRODUCTION_REAL','HISTORICAL_REPLAY','RECONSTRUCTED_ASOF','ACTIVATION_SIMULATION')
PARTITION=('capability','evidence_lane','model_contract_id','parameter_digest','state_lineage_id')
STATES=('PENDING_NOT_DUE','PENDING_SOURCE_UNAVAILABLE','RIGHT_CENSORED','OBSERVED','INVALIDATED_BY_CONTRACT')


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()


def partition(row):
    return tuple(row[k] for k in PARTITION)


def real(row):
    mode='SHADOW' if row['evidence_lane']=='SHADOW_REAL' else 'PRODUCTION'
    return row['evidence_lane'] in ('SHADOW_REAL','PRODUCTION_REAL') and row.get('evidence_origin')=='PIT_OBSERVED' and row.get('accepted_real_publication') is True and row.get('execution_mode')==mode


def validate(value):
    errors=[]; originals={}; event_ids={}
    required={'sessions':set(PARTITION)|{'trade_date','market_session_id','slot_status','evaluable','publication_id','publication_revision','evidence_origin','execution_mode','accepted_real_publication'},'events':set(PARTITION)|{'logical_event_id','enrollment_id','eligible','displayed','T0','control_assignment_ids','benchmark_ids','evidence_origin','execution_mode','accepted_real_publication'},'outcomes':set(PARTITION)|{'due_id','enrollment_id','horizon','due_date','status','native_status','outcome_revision','source_identity','evidence_origin','execution_mode','accepted_real_publication'}}
    for name,fields in required.items():
        for row in value.get(name,[]):
            if not fields <= set(row): errors.append('LEDGER_SCHEMA_INCOMPLETE')
    if errors: return sorted(set(errors))
    session_ids={}; outcome_ids={}
    if any('market_session_ordinal' not in row for row in value['sessions']): return ['ACCEPTED_CALENDAR_ORDER_REQUIRED']
    for row in value['sessions']:
        key=partition(row)+(row['market_session_id'],row['publication_revision'])
        if key in session_ids and session_ids[key]!=digest(row): errors.append('CONFLICTING_SESSION_CONTENT')
        session_ids[key]=digest(row)
    for event in value['events']:
        identity=event['logical_event_id']
        if identity in originals and originals[identity]!=event['enrollment_id']: errors.append('DUPLICATE_ORIGINAL_ENROLLMENT')
        if identity in event_ids and event_ids[identity]!=digest(event): errors.append('CONFLICTING_EVENT_CONTENT')
        originals[identity]=event['enrollment_id']; event_ids[identity]=digest(event)
        if event.get('eligibility_inputs_include_outcomes'): errors.append('SAME_DAY_OUTCOME_FEEDBACK_FORBIDDEN')
    for row in value['sessions']+value['events']+value['outcomes']:
        if any(k not in row for k in PARTITION) or row.get('capability') not in CAPS or row.get('evidence_lane') not in LANES: errors.append('ROW_PARTITION_UNKNOWN')
        if row.get('publication_capability')!=row.get('capability'): errors.append('PUBLICATION_CAPABILITY_MISMATCH')
    for outcome in value['outcomes']:
        key=partition(outcome)+(outcome['due_id'],outcome['outcome_revision'])
        if key in outcome_ids and outcome_ids[key]!=digest(outcome): errors.append('CONFLICTING_OUTCOME_REVISION')
        outcome_ids[key]=digest(outcome)
        if outcome['status'] not in STATES: errors.append('OBSERVATION_STATUS_UNKNOWN')
        if outcome['status']=='OBSERVED' and outcome.get('native_status')!='OBSERVED': errors.append('NATIVE_STATUS_CANNOT_PROMOTE_OBSERVED')
        if outcome['status']=='RIGHT_CENSORED' and (outcome.get('native_status')!='RIGHT_CENSORED' or not outcome.get('right_censor_reason')): errors.append('RIGHT_CENSOR_OWNER_REASON_REQUIRED')
    if value.get('expected_prior_head')!=value.get('actual_prior_head'): errors.append('OBSERVATION_HEAD_CAS_CONFLICT')
    return sorted(set(errors))


def readback(value):
    """Counts supplied synthetic ledger rows; never computes due dates or outcomes."""
    errors=validate(value)
    if errors: return dict(status='BLOCKED_AFFECTED_SCOPE',errors=errors,actual_real_rows_written=0,production_grant=False)
    groups={}; canonical_sessions={}
    for row in value['sessions']:
        key=partition(row)+(row['market_session_id'],)
        if key not in canonical_sessions or row['publication_revision']>canonical_sessions[key]['publication_revision']: canonical_sessions[key]=row
    for session in sorted(canonical_sessions.values(),key=lambda row:row['market_session_ordinal']):
        key=partition(session); group=groups.setdefault(key,dict(session_denominator=0,real_accepted_sessions=0,consecutive_accepted_sessions=0,events=0,hidden_eligible=0,due_denominator=0,observed=0,pending=0,right_censored=0,invalidated=0,native_status_breakdown={}))
        group['session_denominator']+=1
        accepted=real(session) and session['slot_status']=='ACCEPTED' and session['evaluable'] is True
        group['real_accepted_sessions']+=int(accepted)
        group['consecutive_accepted_sessions']=group['consecutive_accepted_sessions']+1 if accepted else 0
    seen=set()
    for event in value['events']:
        if not real(event) or not event['eligible']: continue
        key=partition(event); group=groups[key]
        if event['logical_event_id'] in seen: continue
        seen.add(event['logical_event_id']); group['events']+=1; group['hidden_eligible']+=int(not event['displayed'])
    # Revision projections are distinct views, never additions to the due denominator.
    first={}; latest={}
    for outcome in value['outcomes']:
        if not real(outcome): continue
        key=partition(outcome)+(outcome['due_id'],)
        if key not in first or outcome['outcome_revision']<first[key]['outcome_revision']: first[key]=outcome
        if key not in latest or outcome['outcome_revision']>latest[key]['outcome_revision']: latest[key]=outcome
    for row in latest.values():
        group=groups[partition(row)]; group['due_denominator']+=1
        status=row['status']; field={'OBSERVED':'observed','RIGHT_CENSORED':'right_censored','INVALIDATED_BY_CONTRACT':'invalidated'}.get(status,'pending')
        group[field]+=1; native=row['native_status']; group['native_status_breakdown'][native]=group['native_status_breakdown'].get(native,0)+1
    return dict(status='PASS_DESIGN_ONLY',breakdown=[dict(zip(PARTITION,key),**group) for key,group in sorted(groups.items())],first_observed_revision_view=[dict(due_id=r['due_id'],revision=r['outcome_revision'],status=r['status']) for r in first.values()],latest_corrected_revision_view=[dict(due_id=r['due_id'],revision=r['outcome_revision'],status=r['status']) for r in latest.values()],idempotency_digest=digest(value),actual_real_rows_written=0,production_grant=False)


def fixture():
    common=dict(capability='STOCK_CORE',publication_capability='STOCK_CORE',evidence_lane='SHADOW_REAL',model_contract_id='SIM_MODEL',parameter_digest='SIM_PARAMETERS',state_lineage_id='SIM_LINEAGE',evidence_origin='PIT_OBSERVED',execution_mode='SHADOW',accepted_real_publication=True)
    session=dict(common,trade_date='SIM_T0',market_session_id='SIM_SESSION',market_session_ordinal=1,slot_status='ACCEPTED',evaluable=True,source_availability='AVAILABLE',missed_reason=None,publication_id='SIM_PUB',publication_revision=1)
    event=dict(common,logical_event_id='SIM_EVENT',enrollment_id='SIM_ENROLLMENT',event_type='FIRST_PREWATCH',entity_id='SIM_STOCK',T0='SIM_T0',original_revision=1,eligible=True,displayed=True,control_assignment_ids=['SIM_CONTROL'],benchmark_ids=['SIM_BENCHMARK'])
    outcome=dict(common,due_id='SIM_DUE',enrollment_id='SIM_ENROLLMENT',horizon=5,due_date='SIM_T5',status='OBSERVED',native_status='OBSERVED',outcome_revision=1,source_identity='SIM_SOURCE',observed_at='SIM_T5',right_censor_reason=None,supersedes=None)
    return dict(kind='CONTRACT_DESIGN_SIMULATION',sessions=[session],events=[event],outcomes=[outcome],expected_prior_head='SIM_HEAD',actual_prior_head='SIM_HEAD')


def scenario(index):
    v=fixture()
    if index in (2,3,4):
        lane={2:'ACTIVATION_SIMULATION',3:'HISTORICAL_REPLAY',4:'RECONSTRUCTED_ASOF'}[index]
        for row in v['sessions']+v['events']+v['outcomes']: row.update(evidence_lane=lane,evidence_origin=lane,execution_mode='REPLAY',accepted_real_publication=False)
    if index in (5,6):
        v['sessions'].append(dict(v['sessions'][0],market_session_id='SIM_NEXT',market_session_ordinal=2,trade_date='SIM_NEXT',slot_status='MISSED' if index==5 else 'NON_EVALUABLE',evaluable=False,missed_reason='SIM_UNAVAILABLE'))
    if index==7: v['events'][0]['displayed']=False
    if index==8: v['events'].append(dict(v['events'][0],enrollment_id='SECOND_ORIGINAL'))
    if index==9: v['outcomes'][0].update(status='PENDING_NOT_DUE',native_status='PENDING',observed_at=None)
    if index==10: v['outcomes'][0].update(status='RIGHT_CENSORED',native_status='RIGHT_CENSORED',right_censor_reason='REPORT_CUTOFF',observed_at=None)
    if index==11: v['outcomes'].append(dict(v['outcomes'][0],outcome_revision=2,source_identity='SIM_CORRECTED',supersedes='SIM_REV1'))
    if index in (12,13):
        field='model_contract_id' if index==12 else 'parameter_digest'
        next_session=dict(v['sessions'][0],market_session_id='SIM_NEW',market_session_ordinal=2,trade_date='SIM_NEW'); next_session[field]='SIM_CHANGED'
        v['sessions'].append(next_session)
        if index==13:
            for ordinal in (1,2): v['sessions'].append(dict(v['sessions'][0],capability='SECTOR_STAGE',publication_capability='SECTOR_STAGE',market_session_id='SIM_SECTOR_'+str(ordinal),market_session_ordinal=ordinal))
    if index in (15,16,20):
        for name in ('sessions','events','outcomes'):
            new=dict(v[name][0],evidence_lane='PRODUCTION_REAL',execution_mode='PRODUCTION')
            if name=='sessions': new.update(market_session_id='SIM_PROD_SESSION',publication_id='SIM_PROD_PUB')
            if name=='events': new.update(logical_event_id='SIM_PROD_EVENT',enrollment_id='SIM_PROD_ENROLLMENT')
            if name=='outcomes': new.update(due_id='SIM_PROD_DUE',enrollment_id='SIM_PROD_ENROLLMENT')
            v[name].append(new)
    if index==18: v['actual_prior_head']='OTHER_HEAD'
    if index==19: v['events'][0]['eligibility_inputs_include_outcomes']=True
    return v


def vector_result(index):
    v=scenario(index); result=readback(v)
    if index==14: result['sector_counts_borrowed']=False; result['sector_real_events']=sum(r['events'] for r in result['breakdown'] if r['capability']=='SECTOR_STAGE')
    if index==17: result['identical_rerun_same_digest']=readback(deepcopy(v))['idempotency_digest']==result['idempotency_digest']
    return result
