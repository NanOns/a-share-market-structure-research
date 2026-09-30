"""Freeze §30-33/78 interface and manually specified independent oracle vectors."""
from copy import deepcopy
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.build_v4_08_r2_membership_evidence import atomic_json, atomic_bytes
from scripts.promote_v4_09_accepted_head import bind, validate

MASTER='docs/evidence/A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_REV4_FEP_R2_20260930.md'
TASK='docs/evidence/V4_09_ACCEPTED_HEAD_PROMOTION_AND_V4_10_STATE_REDUCER_ENTRY_TASK_20260930.md'
ORDER=['R1_MODEL_BOUNDARY','R2_HARD_INVALIDATION','R3_REQUIRED_UNKNOWN','R4_STAGE_SELECTION',
       'R5_HYSTERESIS','R6_HEALTH','R7_TRACKING','R8_EXPIRY','R9_REENTRY']
AXES=dict(maturity=['NONE','SEED','PREWATCH','WARM','CONFIRMED'],
    health=['IMPROVING','STABLE','WEAKENING','DAMAGED','EXHAUSTED','UNKNOWN'],
    validity=['VALID','INVALIDATED','UNKNOWN'],tracking=['ACTIVE','FOLLOWUP','CLOSED'],
    scenario=dict(STOCK=['SETUP','LAUNCH_CONFIRM','RECOVERY_TURN','STRONG_PULLBACK','TREND_CONTINUE','NONE'],
                  SECTOR=['BASE_BUILD','BREADTH_BUILD','RECOVERY_BUILD','BROADENING','REACCELERATING','SUSTAINED','NONE']))

def fixture(entity_type='STOCK', stage='PREWATCH'):
    detectors={s:dict(value='TRUE' if s==stage else 'FALSE',status='SYNTHETIC',contract_id='SYNTHETIC_'+s,
        parameter_set_id='FIXTURE_PARAMETERS_V1',publication_id='FIXTURE_FACTS') for s in ['CONFIRMED','WARM','PREWATCH','SEED']}
    if entity_type=='STOCK': detectors['WARM'].update(value='UNKNOWN',status='NOT_APPLICABLE')
    return dict(entity_id='fixture-entity',entity_type=entity_type,trade_date='2026-09-28',session_index=20,
        calendar_publication_id='FIXTURE_MARKET_CALENDAR_V1',mode='SYNTHETIC_CONTRACT_VECTOR',input_publication_ids=['FIXTURE_FACTS'],
        prior_state=None,prior_state_binding=None,model_boundary=False,suspended=False,followup_complete=False,
        detectors=detectors,core_price_damage='FALSE',frozen_invalidation=dict(value='FALSE',episode_id=None,contract_id=None),
        episode_invalidation_contract_id='FIXTURE_EPISODE_INVALIDATION_V1',delta3=0,dq5=0,risk='LOW',
        scenario=dict(value='NONE',status='KNOWN'))

def prior(stage='PREWATCH', **updates):
    row=dict(entity_id='fixture-entity',entity_type='STOCK',publication_id='FIXTURE_PRIOR',session_index=19,
        model_contract_id='RESEARCH_STATE_V1',parameter_set_id='V4_10_STATE_REDUCER_PARAMETER_SET_V1',
        maturity=stage,health='STABLE',validity='VALID',tracking='ACTIVE',scenario='SETUP',scenario_status='KNOWN',
        state_freshness='FRESH',final_eligibility='TRUE',episode_id='FIXTURE_EPISODE',parent_episode_id=None,
        invalidation_contract_id='FIXTURE_EPISODE_INVALIDATION_V1',downgrade_candidate=None,downgrade_count=0,
        expiry_count=4,improvement_baseline=0,market_age=4,exit_session_index=None,preserved_followup_episode_ids=[])
    row.update(updates)
    if row['entity_type']=='SECTOR' and row['scenario']=='SETUP': row['scenario']='BASE_BUILD'
    return row

def with_prior(x, row):
    # Only a canonical payload hash, no reducer implementation or rule oracle is imported.
    import hashlib,json
    x['prior_state']=row
    x['prior_state_binding']=dict(publication_id=row['publication_id'],payload_digest=hashlib.sha256(
        json.dumps(row,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest())
    return x

def vectors():
    rows=[]
    def add(name,x,expected,tag,error=None):
        rows.append(dict(id=name,input=x,expected=expected,coverage=tag,expected_error=error))
    # Expected values are declared here, never derived from runtime results.
    for kind in ['STOCK','SECTOR']:
        for stage in ['NONE','SEED','PREWATCH','CONFIRMED']+(['WARM'] if kind=='SECTOR' else []):
            x=fixture(kind,stage)
            add(kind+'_'+stage,x,dict(maturity=stage,health='STABLE',validity='VALID',state_freshness='FRESH',
                final_eligibility='FALSE' if stage=='NONE' else 'TRUE',tracking='CLOSED' if stage=='NONE' else 'ACTIVE'),['stage_selection','axes'])
    x=fixture();x['detectors']['SEED']['value']='TRUE'
    add('prewatch_over_seed',x,dict(maturity='PREWATCH'),['PREWATCH_GT_SEED'])
    x=fixture();x['detectors']['CONFIRMED']['value']='TRUE'
    add('confirmed_over_prewatch',x,dict(maturity='CONFIRMED'),['CONFIRMED_GT_PREWATCH'])
    for kind in ['STOCK','SECTOR']:
        for metric,health in [(-3.01,'WEAKENING'),(-3,'STABLE'),(-2.99,'STABLE'),(0,'STABLE'),(2.99,'STABLE'),(3,'STABLE'),(3.01,'IMPROVING'),(None,'UNKNOWN')]:
            x=fixture(kind,'CONFIRMED');x['delta3' if kind=='STOCK' else 'dq5']=metric
            add(kind+'_health_'+str(metric),x,dict(health=health,final_eligibility='TRUE',validity='VALID'),['health_boundaries','health_unknown'])
        x=fixture(kind,'CONFIRMED');x['risk']='EXTREME';x['delta3']=None;x['dq5']=None
        add(kind+'_extreme',x,dict(health='EXHAUSTED'),['risk_extreme'])
    for axis in ['SEED','PREWATCH','CONFIRMED','core_price_damage','frozen_invalidation']:
        x=with_prior(fixture(),prior())
        if axis in x['detectors']: x['detectors'][axis]['value']='UNKNOWN'
        elif axis=='frozen_invalidation': x[axis]['value']='UNKNOWN'
        else: x[axis]='UNKNOWN'
        add('unknown_'+axis,x,dict(maturity='PREWATCH',health='UNKNOWN',validity='UNKNOWN',tracking='ACTIVE',
            final_eligibility='UNKNOWN',state_freshness='STALE',episode_id='FIXTURE_EPISODE',downgrade_count=0,expiry_count=4),
            ['required_unknown','maturity_unknown_preservation','tracking_unknown_preservation'])
    for hard in ['core_price_damage','frozen_invalidation']:
        x=with_prior(fixture(stage='CONFIRMED'),prior())
        x['detectors']['SEED']['value']='UNKNOWN'
        if hard=='core_price_damage': x[hard]='TRUE'
        else: x[hard].update(value='TRUE',episode_id='FIXTURE_EPISODE',contract_id='FIXTURE_EPISODE_INVALIDATION_V1')
        add('hard_'+hard,x,dict(maturity='NONE',health='DAMAGED',validity='INVALIDATED',tracking='FOLLOWUP',final_eligibility='FALSE'),['hard_over_confirmation','hard_over_unknown'])
    x=with_prior(fixture(),prior());x['frozen_invalidation'].update(value='TRUE',episode_id='unrelated',contract_id='FIXTURE_EPISODE_INVALIDATION_V1')
    add('unrelated_anchor_fail_closed',x,dict(validity='UNKNOWN',maturity='PREWATCH',final_eligibility='UNKNOWN'),['episode_invalidation_scope'])
    for stage in ['NONE','SEED']:
        for day in [1,2]:
            row=prior(downgrade_candidate=stage if day==2 else None,downgrade_count=1 if day==2 else 0)
            x=with_prior(fixture(stage=stage),row)
            add('downgrade_'+stage+'_day'+str(day),x,dict(maturity='PREWATCH' if day==1 else stage,
                final_eligibility='FALSE' if stage=='NONE' else 'TRUE',downgrade_count=day,
                tracking='FOLLOWUP' if stage=='NONE' and day==2 else 'ACTIVE',episode_id='FIXTURE_EPISODE'),['downgrade_day'+str(day)])
    x=with_prior(fixture(stage='CONFIRMED'),prior())
    add('upgrade_immediate',x,dict(maturity='CONFIRMED',episode_id='FIXTURE_EPISODE',downgrade_count=0),['upgrade_immediate','no_episode_for_stage_change'])
    for interrupted in ['UNKNOWN','SUSPENSION','SESSION_GAP']:
        x=with_prior(fixture(stage='NONE'),prior(downgrade_candidate='NONE',downgrade_count=1))
        if interrupted=='UNKNOWN':x['detectors']['SEED']['value']='UNKNOWN'
        elif interrupted=='SUSPENSION':x['suspended']=True
        else:x['session_index']=21
        add('break_'+interrupted,x,dict(maturity='PREWATCH',downgrade_count=1 if interrupted=='SESSION_GAP' else 0,
            final_eligibility='FALSE' if interrupted=='SESSION_GAP' else 'UNKNOWN'),['hysteresis_break'])
    for count in [8,9]:
        x=with_prior(fixture(),prior(expiry_count=count))
        add('expiry_'+str(count+1),x,dict(expiry_count=count+1,maturity='NONE' if count==9 else 'PREWATCH',
            tracking='FOLLOWUP' if count==9 else 'ACTIVE',final_eligibility='FALSE' if count==9 else 'TRUE',
            improvement_baseline=0),['expiry_boundary'])
    for improvement in [2.99,3,3.01]:
        x=with_prior(fixture(),prior(expiry_count=9));x['delta3']=improvement
        add('expiry_improvement_'+str(improvement),x,dict(expiry_count=10 if improvement<3 else 1,
            improvement_baseline=0 if improvement<3 else improvement,maturity='NONE' if improvement<3 else 'PREWATCH'),['expiry_baseline_frozen'])
    for interruption in ['UNKNOWN','SUSPENSION','HEALTH_HISTORY']:
        x=with_prior(fixture(),prior(expiry_count=9))
        if interruption=='UNKNOWN':x['detectors']['SEED']['value']='UNKNOWN'
        elif interruption=='SUSPENSION':x['suspended']=True
        else:x['delta3']=None
        add('expiry_pause_'+interruption,x,dict(expiry_count=9,market_age=5,maturity='PREWATCH',improvement_baseline=0),['expiry_unknown_pause','market_age'])
    for kind in ['STOCK','SECTOR']:
        for stage in ['CONFIRMED']+(['WARM'] if kind=='SECTOR' else []):
            x=with_prior(fixture(kind,stage),prior(stage,entity_type=kind,expiry_count=99))
            add('expiry_na_'+kind+stage,x,dict(maturity=stage,expiry_count=0),['expiry_not_applicable'])
    for session in [20,21,22]:
        x=with_prior(fixture(),prior('NONE',session_index=20,exit_session_index=20,tracking='FOLLOWUP',expiry_count=0))
        x['session_index']=session
        add('reentry_session_'+str(session),x,dict(maturity='NONE' if session==20 else 'PREWATCH',
            final_eligibility='FALSE' if session==20 else 'TRUE',tracking='FOLLOWUP' if session==20 else 'ACTIVE',
            parent_episode_id=None if session==20 else 'FIXTURE_EPISODE'),['same_day_reentry_forbidden' if session==20 else 'next_session_reentry'])
    x=with_prior(fixture(),prior());x['model_boundary']=True
    add('model_boundary',x,dict(parent_episode_id=None,tracking='ACTIVE'),['model_boundary_not_reentry'])
    for done in [False,True]:
        x=with_prior(fixture(stage='NONE'),prior('NONE',tracking='FOLLOWUP',exit_session_index=17));x['followup_complete']=done
        add('tracking_complete_'+str(done),x,dict(tracking='CLOSED' if done else 'FOLLOWUP'),['tracking'])
    for kind,scenarios in AXES['scenario'].items():
        for scenario in scenarios:
            x=fixture(kind);x['scenario']['value']=scenario
            add(kind+'_scenario_'+scenario,x,dict(scenario=scenario,scenario_status='KNOWN'),['scenario_axis'])
    x=with_prior(fixture(),prior());x['scenario']['status']='UNKNOWN'
    add('scenario_unknown',x,dict(scenario='SETUP',scenario_status='UNKNOWN',validity='VALID'),['scenario_unknown'])
    for stage in ['NONE','SEED','PREWATCH','WARM','CONFIRMED']:
        x=with_prior(fixture('SECTOR'),prior(stage,entity_type='SECTOR'));x['detectors']['CONFIRMED']['value']='UNKNOWN'
        add('last_known_'+stage,x,dict(maturity=stage,tracking='ACTIVE',validity='UNKNOWN'),['all_maturity_preserved'])
    for tracking in ['ACTIVE','FOLLOWUP','CLOSED']:
        x=with_prior(fixture(),prior(tracking=tracking));x['detectors']['CONFIRMED']['value']='UNKNOWN'
        add('tracking_unknown_'+tracking,x,dict(tracking=tracking),['all_tracking_preserved'])
    for missing in ['CONFIRMED','WARM']:
        x=fixture('SECTOR');x['detectors'][missing].update(status='NOT_IMPLEMENTED',value='UNKNOWN')
        add('missing_'+missing,x,dict(final_eligibility='UNKNOWN',maturity='NONE',tracking='CLOSED'),['not_implemented_inputs'])
    for bad in ['TRUE','FALSE']:
        x=fixture();x['detectors']['WARM'].update(status='SYNTHETIC',value=bad)
        add('stock_warm_illegal_'+bad,x,{},['stock_warm_na'],error='STOCK_WARM_NOT_APPLICABLE_REQUIRED')
    x=fixture();x['mode']='ACCEPTED_FACT_INTERFACE'
    add('synthetic_in_real_input_reject',x,{},['no_fake_detector'],error='SYNTHETIC_DETECTOR_IN_ACCEPTED_INPUT')
    x=with_prior(fixture(),prior());x['prior_state_binding']['payload_digest']='wrong'
    add('prior_digest_reject',x,{},['prior_binding'],error='PRIOR_STATE_BINDING_MISMATCH')
    x=with_prior(fixture(),prior(model_contract_id='OLD_MODEL'))
    add('unmarked_boundary_reject',x,{},['model_boundary_lineage'],error='MODEL_BOUNDARY_REQUIRED')
    x=fixture();x['core_price_damage']=False
    add('unknown_false_coercion_reject',x,{},['no_unknown_to_false'],error='INVALID_TRI_STATE')
    x=with_prior(fixture(),prior('WARM'))
    add('stock_prior_warm_reject',x,{},['stock_warm_na'],error='ILLEGAL_STOCK_WARM_PRIOR')
    for field,value in [('contract_id','WRONG'),('parameter_set_id','WRONG'),('publication_id','UNBOUND')]:
        x=fixture();x['detectors']['PREWATCH'].update(status='IMPLEMENTED',contract_id='STOCK_PREWATCH_V1',
            parameter_set_id='V4_09_STOCK_PREWATCH_PARAMETER_SET_V1')
        x['detectors']['PREWATCH'][field]=value
        add('producer_wrong_'+field,x,dict(final_eligibility='UNKNOWN',maturity='NONE',tracking='CLOSED',
            raw_qualification={'CONFIRMED':'FALSE','PREWATCH':'UNKNOWN','SEED':'FALSE'}),['producer_lineage_gate'])
    x=with_prior(fixture(stage='NONE'),prior(session_index=20,downgrade_candidate='NONE',downgrade_count=1))
    add('downgrade_same_session_revision',x,dict(downgrade_count=1,maturity='PREWATCH'),['revision_no_counter_advance'])
    x=with_prior(fixture(),prior(session_index=20,expiry_count=9))
    add('expiry_same_session_revision',x,dict(expiry_count=9,maturity='PREWATCH'),['revision_no_counter_advance'])
    return rows

def main():
    if validate()['status']!='PASS':raise ValueError('V4_09_PROMOTION_REQUIRED')
    required=list(fixture())
    contract=dict(contract_id='RESEARCH_STATE_V1',version='1.0.0',authority=dict(master=bind(MASTER),task=bind(TASK),sections=['30','31','32','33','78']),
        scope='INTERFACE_AND_INDEPENDENT_SYNTHETIC_VECTORS_ONLY',rule_order=ORDER,axes=AXES,input_required_fields=required,
        risk_domain=['LOW','MEDIUM','HIGH','EXTREME','UNKNOWN'],producer_contracts=dict(SEED='BASE_SEED_V1',PREWATCH='STOCK_PREWATCH_V1'),
        producer_parameters=dict(SEED='V4_07_BASE_SEED_PARAMETER_SET_V1',PREWATCH='V4_09_STOCK_PREWATCH_PARAMETER_SET_V1'),
        missing_inputs=dict(confirmation='NOT_IMPLEMENTED_V4_11',structure_anchor_support='NOT_IMPLEMENTED_V4_12',
            frozen_episode_invalidation='NOT_IMPLEMENTED_V4_12',stock_warm='NOT_APPLICABLE',sector_legacy_warm='NOT_IMPLEMENTED_UNACCEPTED_EXTRACTION'),
        unknown_semantics=dict(required='preserve last-known maturity/tracking/scenario; STALE; health/validity/eligibility UNKNOWN; no enrollment/exit',
            health_history='health UNKNOWN only; expiry cannot increment without improvement history',scenario='preserve prior axis value with scenario_status UNKNOWN'),
        expiry_semantics=dict(first_qualifying_session_count=1,unknown_suspension='pause count; market_age advances',
            improvement_baseline='freeze until >=3pp cumulative improvement or stage upgrade',stage_upgrade='reset count to 1',
            applicable=['SEED','PREWATCH'],same_session_revision='does not advance counters'),
        lineage='exact prior payload digest, prior publication ID, entity/type, monotone bound market-calendar session index',
        hard_invalidation_scope='associated episode and frozen creation contract only',
        permissions=dict(production=False,shadow=False,focus_cutover=False),next_stage='INDEPENDENT_EXTERNAL_REAUDIT')
    ast=dict(contract_id='V4_10_REDUCER_MACHINE_AST_V1',rule_order=ORDER,stage_precedence=['CONFIRMED','WARM','PREWATCH','SEED'],
        rules=[dict(id=r,operation=op) for r,op in zip(ORDER,['SELECT_LEGAL_PRIOR_OR_MODEL_BOUNDARY','EPISODE_INVALIDATION_OR_CORE_DAMAGE_FIRST',
            'PRESERVE_IF_REQUIRED_UNKNOWN_OR_SUSPENDED','HIGHEST_LEGAL_TRUE_STAGE','IMMEDIATE_UPGRADE_TWO_EVALUABLE_SESSION_DOWNGRADE',
            'EXTREME_ELSE_METRIC_DEADBAND','ACTIVE_FOLLOWUP_CLOSED','FROZEN_BASELINE_EVALUABLE_SESSION_EXPIRY','NEW_CHILD_EPISODE_AFTER_EXIT_SESSION'])],
        parameters=dict(downgrade='downgrade_sessions',health='health_deadband_pp',expiry='expiry_sessions',improvement='expiry_improvement_pp'))
    ast['predicates']=dict(hard_invalidation={'op':'AND','args':['prior_episode_exists',{'op':'OR','args':['associated_frozen_invalidation_TRUE','core_price_damage_TRUE']}]},
        required_unknown={'op':'OR','args':['any_required_applicable_fact_UNKNOWN','suspended']},
        upgrade={'op':'GT','args':['raw_stage_rank','prior_stage_rank']},
        downgrade={'op':'AND','args':[{'op':'LT','args':['raw_stage_rank','prior_stage_rank']},{'op':'GTE','args':['consecutive_evaluable_sessions',{'parameter':'downgrade_sessions'}]}]},
        health_improving={'op':'GT','args':['delta3_or_dq5',{'parameter':'health_deadband_pp'}]},
        health_weakening={'op':'LT','args':['delta3_or_dq5',{'op':'NEGATE','arg':{'parameter':'health_deadband_pp'}}]},
        expiry={'op':'AND','args':['maturity_in_SEED_PREWATCH','no_stage_upgrade','improvement_below_threshold',{'op':'GTE','args':['expiry_count',{'parameter':'expiry_sessions'}]}]},
        reentry={'op':'AND','args':['prior_formally_exited','current_qualification_TRUE',{'op':'GT','args':['session_index','exit_session_index']}]})
    params=dict(parameter_set_id='V4_10_STATE_REDUCER_PARAMETER_SET_V1',version='1.0.0',authority=bind(MASTER),
        downgrade_sessions=2,health_deadband_pp=3,expiry_sessions=10,expiry_improvement_pp=3)
    input_schema=dict(schema_id='V4_10_REDUCER_INPUT_SCHEMA_V1',type='object',required=required,
        facts_domain=['TRUE','FALSE','UNKNOWN'],detector_status=['IMPLEMENTED','SYNTHETIC','NOT_IMPLEMENTED','NOT_APPLICABLE'],
        provenance_required=['contract_id','parameter_set_id','publication_id'],no_implicit_false=True,
        prior_state_binding=['publication_id','payload_digest'],session_index='explicit bound market calendar; nonnegative integer')
    output_schema=dict(schema_id='V4_10_REDUCER_OUTPUT_SCHEMA_V1',type='object',axes=AXES,
        required=['publication_id','entity_id','entity_type','trade_date','session_index','calendar_publication_id','mode','maturity','health','validity','tracking','scenario',
            'scenario_status','state_freshness','final_eligibility','raw_qualification','detector_statuses','episode_id','parent_episode_id',
            'prior_state_binding','input_publication_ids','model_contract_id','parameter_set_id','input_digest','matched_predicates','unknown_predicates',
            'transition_reasons','expiry_count','improvement_baseline','market_age','downgrade_candidate','downgrade_count','exit_session_index','boundary_event','preserved_followup_episode_ids'],
        final_eligibility=['TRUE','FALSE','UNKNOWN'],state_freshness=['FRESH','STALE'],
        persistence='append-only engineering publication + entity/type/episode-scoped results; no UPDATE/DELETE')
    files=dict(research_state_contract=contract,machine_ast=ast,parameter_set=params,input_schema=input_schema,output_schema=output_schema,
        machine_vectors=dict(contract_id='V4_10_INDEPENDENT_MACHINE_VECTORS_V1',oracle='MANUALLY_DECLARED_EXPECTED_VALUES_NO_RUNTIME_HELPER',vectors=vectors()))
    for name,value in files.items():atomic_json(ROOT/f'config/v4_10_{name}_v1.json',value)
    atomic_json(ROOT/'reports/v4_10/V4_10_CONTRACT_FREEZE.json',dict(contract_id='V4_10_CONTRACT_FREEZE_V1',status='PASS_INTERFACE_SCOPE_FREEZE',
        authority=bind(MASTER),stage_task=bind(TASK),accepted_upstream=bind('data/v4/V4_09_ACCEPTED_HEAD.json'),
        bindings={n:bind(f'config/v4_10_{n}_v1.json') for n in files},next_stage='INTERFACE_ENGINEERING_THEN_EXTERNAL_REAUDIT'))
    atomic_bytes(ROOT/'reports/v4_10/V4_10_STAGE_ENTRY.md',('''# V4-10 State Reducer engineering entry — 2026-10-01

Authority: REV4 FEP R2 §§30–33/78 and the 2026-09-30 promotion/entry task.
V4-09 exact promotion validation PASS; Phase 0 FULL_PASS; upstream is the amended V4-08 head.
Authorized: RESEARCH_STATE_V1 interface, schemas, axes, precedence, UNKNOWN, hysteresis, expiry/reentry, independent synthetic vectors and append-only engineering persistence.
No complete D0/D1/D2 DAG. V4-11 Confirmation and V4-12 Structure/Anchor/Support and full frozen episode invalidation remain NOT_IMPLEMENTED. Stock WARM is NOT_APPLICABLE; sector legacy WARM extraction remains unaccepted. Synthetic positives are fixture-only.
Acceptance target: V4_10_REDUCER_INTERFACE_ENGINEERING_CANDIDATE_READY_FOR_EXTERNAL_REAUDIT. Full integrated acceptance remains V4-14 Replay Gate B.
OPEN audits: V4_07_PRIOR_RPS_ACCEPTED_INPUT_BOOTSTRAP_01, AUD-AMOUNT-A-06, DM01_REAL_INCREMENTAL_BUILDERS, LEGACY_VALID_MEMBER_EXACT_PRODUCER, FORWARD_PIT_HISTORY_ACCUMULATION. They retain separate scope and acceptance.
Production, shadow production and Focus/UI cutover permissions remain false. TDX sources remain read-only. After this stage, stop for independent external reaudit; a Git push is not external acceptance.
''').encode())
    print('frozen vectors:',len(files['machine_vectors']['vectors']))

if __name__=='__main__':
    from scripts.freeze_v4_10_r1_1_contract import main as repair_main
    repair_main()
