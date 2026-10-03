"""Independent static contract oracle. Contains no publisher or settlement evaluator."""
import json
import math
from pathlib import Path
from scripts.validate_r19a_promotion import validate as promotion, require

ROOT=Path(__file__).resolve().parents[1]
B_NAMES=['radar_contract','radar_event_registry','why_now_schema','conflict_hypothesis_schema','cohort_contract','cohort_revision_policy','radar_cohort_field_registry','radar_cohort_machine_vectors']
C_NAMES=['due_planner_contract','forward_price_path_contract','outcome_status_contract','competing_outcome_contract','forward_market_benchmark_contract','forward_sector_benchmark_contract','rotation_pulse_basket_contract','control_assignment_contract','settlement_revision_contract','settlement_readback_contract','settlement_field_registry','settlement_machine_vectors']
D_NAMES=['field_registry','dag_registry','source_capability_matrix','quality_degradation','machine_vectors','storage_schema_design']
LKEY=['model_contract_id','state_lineage_id','publication_id','entity_type','entity_id','signal_type']
EKEY=['model_contract_id','state_lineage_id','entity_type','entity_id','episode_id','event_type','event_trade_date']
OKEY=['enrollment_id','horizon','outcome_contract_id','evaluation_source_digest']
EVENTS=['FIRST_PREWATCH','REENTRY_PREWATCH','UPGRADE_TO_WARM','NEW_CONFIRMED','REACCELERATION_EVENT','INVALIDATION']
STATES=['PENDING','RIGHT_CENSORED','OBSERVED','SUSPENDED_AT_HORIZON','MATURED_DATA_MISSING','DELISTED_BEFORE_HORIZON','IDENTITY_UNKNOWN','ADJUSTMENT_UNKNOWN']
NONEDGES=[['Focus','enrollment'],['UI Top-K','enrollment'],['Forward outcome','T0 state'],['FEP prediction','Core/Radar'],['Corrected outcome','T0'],['future source','same-day decision']]
NODES=['Accepted V4-14 publication','Radar event projection','complete daily ledger','logical event / observation','first ASSERTED enrollment','frozen benchmark + controls','due planner','future accepted source readback','settlement / outcome revision','readback / statistics consumers']
CAPS=['RADAR_EVENT_PROJECTION','VALIDATION_COHORT','ABSOLUTE_FORWARD_SETTLEMENT','MARKET_RELATIVE_SETTLEMENT','SECTOR_RELATIVE_SETTLEMENT','CONTROL_A_LEGACY','CONTROL_B_DELTA3','CONTROL_C_MATCHED','COMPETING_OUTCOMES','OUTCOME_REVISION_READBACK']

def load(name, overrides=None):
    return (overrides or {}).get(name) or json.loads((ROOT/('config/v4_15_'+name+'_v1.json')).read_bytes())

def fields_check(names, registry, overrides):
    contracts=[load(n,overrides) for n in names if 'field_registry' not in n and 'vectors' not in n]
    # Independently specified fields: removing a field from both its schema and
    # registry must fail, even if the resulting package is self-consistent.
    schema={
        'radar_contract':'daily_ledger logical_event event_observation trade_date eligibility_state eligibility_rank priority_bucket priority_rank display_rank focus_activation_state focus_activation_reason max_source_trade_date publication_digest',
        'radar_event_registry':'event_type event_trade_date episode_id',
        'why_now_schema':'previous_stage current_stage changed_facts changed_domains newly_satisfied_rules new_risk_flags',
        'conflict_hypothesis_schema':'supporting_evidence opposing_evidence unknown_evidence hypothesis_id statement evidence_for evidence_against next_discriminator expiry_condition quality',
        'cohort_contract':'enrollment_id cohort_namespace T0 model_contract_id state_lineage_id entity_type entity_id episode_id signal_type source_publication source_digest parameter_digest contract_digest signal_reference comparison_reference benchmark_ids control_assignment_ids calendar_identity adjustment_identity evidence_class observation_slot observation_deadline accepted_at',
        'cohort_revision_policy':'logical_event_id publication_id observation_state source_correction supersedes_observation',
        'due_planner_contract':'due_trade_date horizon due_state actual_count',
        'forward_price_path_contract':'R_N MFE_N MAE_N PATH_MDD_CLOSE_N evaluation_basis_date evaluation_comparison_reference evaluation_adjustment_identity transform_coefficients transform_digest source_asof available_at price_path',
        'outcome_status_contract':'outcome_status path_quality endpoint_quality reason_codes terminal_value terminal_evidence report_cutoff',
        'competing_outcome_contract':'competing_event first_event_trade_date competing_source_publication censoring_state',
        'forward_market_benchmark_contract':'benchmark_id benchmark_members initial_weights fixed_shares benchmark_constituent_policy benchmark_endpoint_coverage benchmark_missing_weight benchmark_suspended_weight benchmark_delisted_weight benchmark_unknown_weight benchmark_valuation_coverage benchmark_marked_weight benchmark_quality observed_contribution relative_market_return relative_market_return_marked quote_age quote_trade_date',
        'forward_sector_benchmark_contract':'sector_benchmark_id sector_members relative_sector_return relative_sector_return_marked MFE_CLOSE MAE_CLOSE',
        'rotation_pulse_basket_contract':'rotation_basket_id pulse_trade_date pulse_members pulse_reference',
        'control_assignment_contract':'control_assignment_id control_type control_entity_ids match_scope control_feature_snapshot assignment_digest crossed_signal_at control_count control_distance',
        'settlement_revision_contract':'outcome_id outcome_contract_id evaluation_source_digest evaluation_revision supersedes revision_reason first_observed_id latest_corrected_id evaluation_source_identity',
        'settlement_readback_contract':'readback_view readback_asof due_items pending_items matured_items benchmark_control_bindings degradation_reasons'}
    for name in names:
        if name in schema:require(load(name,overrides)['fields']==schema[name].split(), 'INDEPENDENT_REQUIRED_SCHEMA_'+name)
    required={f for c in contracts for f in c['fields']}
    ids=[f['field_id'] for f in registry]
    require(set(ids)==required and len(ids)==len(set(ids)), 'EXACT_UNIQUE_FIELD_AUTHORITY')
    producers={c['contract_id'] for c in contracts}
    for f in registry:
        require(set(['field_id','producer','consumer','type','unit','time_role','source_binding','evidence_class','quality_states','unknown_behavior','not_applicable_behavior','revision_behavior','identity_participation'])<=set(f),'FIELD_METADATA')
        require(f['producer'] in producers and f['field_id'] in next(c['fields'] for c in contracts if c['contract_id']==f['producer']), 'OWNER_FIELD_SCHEMA')
        require(f['time_role'] and f['unknown_behavior']=='NULL_WITH_REASON_NEVER_ZERO_OR_FALSE' and f['not_applicable_behavior']=='NULL_WITH_NOT_APPLICABLE_REASON', 'UNKNOWN_SEMANTICS')
        require(set(f['quality_states'])=={'KNOWN','UNKNOWN','NOT_APPLICABLE','NOT_IMPLEMENTED','DEGRADED'},'QUALITY_ENUM')

def numeric_vectors(vectors):
    for v in vectors:
        i,o=v['input'],v['expected']
        if 'closes' not in i or any(x is None for x in i['closes']): continue
        p=i['closes']; h=i['highs']; low=i['lows']; peak=p[0]; dd=[]
        for close in p: peak=max(peak,close); dd.append(close/peak-1)
        expected={'R_N':p[-1]/p[0]-1,'MFE_N':max([0]+[x/p[0]-1 for x in h]),'MAE_N':min([0]+[x/p[0]-1 for x in low]),'PATH_MDD_CLOSE_N':min(dd)}
        require(o.get('status')=='OBSERVED' and set(o)==set(expected)|{'status'}|({'comparison_reference'} if 'original_P0' in i else set()), 'NUMERIC_VECTOR_COMPLETE_OUTPUT_'+v['case_id'])
        for k,val in expected.items():require(k in o and math.isclose(o[k],val,abs_tol=1e-12), 'INDEPENDENT_FORMULA_'+v['case_id']+'_'+k)
        if 'original_P0' in i:require(o['comparison_reference']==i['alpha']*i['original_P0']+i['beta'],'AFFINE_COMMON_BASIS')

def check_b(overrides=None):
    promotion()
    get=lambda n:load(n,overrides)
    r=get('radar_contract'); e=get('radar_event_registry'); c=get('cohort_contract'); rev=get('cohort_revision_policy')
    require(r['owner_recomputation'] is False and r['complete_ledger'] is True and set(r['forbidden_inputs'])=={'Focus','UI Top-K','Forward outcome','FEP prediction'},'RADAR_READ_ONLY')
    require(e['event_types']==EVENTS and e['persistent_creates_event'] is False and e['stock_warm']=='NOT_APPLICABLE_NO_ACCEPTED_OWNER' and e['missing_owner_event']=='NOT_APPLICABLE_NEVER_SYNTHESIZE','EVENT_OWNER_BOUNDARY')
    require(rev['daily_ledger_key']==LKEY and rev['logical_event_key']==EKEY and rev['observation_key']==['logical_event_id','publication_id'],'EXACT_EVENT_IDENTITIES')
    require(rev['observation_states']==['ASSERTED','RETRACTED','CORRECTED'] and rev['append_only'] and rev['source_correction']==dict(reset_T0=False,redraw_controls=False,erase_as_recorded=False,reconstructed_separate=True),'SOURCE_CORRECTION_INVARIANTS')
    require(set(c['ignore_selection'])=={'Focus','UI Top-K','manual_pin','display_cap'} and c['exited_invalidated_continue_settlement'] and c['enrollment_key']==['logical_event_id','cohort_namespace'],'COMPLETE_COHORT')
    require(c['population']=='ALL_FINAL_ELIGIBLE_STOCK_SECTOR_PREWATCH_WARM_CONFIRMED_SUBJECT_TO_ACCEPTED_OWNER' and c['primary_namespace']=='FIRST_OBSERVED' and c['reconstructed_namespace']=='RECONSTRUCTED_ASOF','COHORT_NAMESPACE')
    require(set(get('why_now_schema')['fields'])==set('previous_stage current_stage changed_facts changed_domains newly_satisfied_rules new_risk_flags'.split()) and get('why_now_schema')['qualification_effect'] is False,'WHY_NOW_NOT_QUALIFICATION')
    hyp=get('conflict_hypothesis_schema')
    require(set('supporting_evidence opposing_evidence unknown_evidence hypothesis_id statement evidence_for evidence_against next_discriminator expiry_condition quality'.split())==set(hyp['fields']) and hyp['eligibility_effect'] is False and hyp['fabricate_second_story'] is False and hyp['insufficient_competition']=='HYPOTHESIS_SET_INCOMPLETE','EXPLANATION_LAYER')
    require(set('enrollment_id cohort_namespace T0 model_contract_id state_lineage_id entity_type entity_id episode_id signal_type source_publication source_digest parameter_digest contract_digest signal_reference comparison_reference benchmark_ids control_assignment_ids calendar_identity adjustment_identity evidence_class observation_slot observation_deadline accepted_at'.split())==set(c['fields']),'ENROLLMENT_COMPLETE')
    fields_check(B_NAMES,get('radar_cohort_field_registry')['registry'],overrides)
    vectors=get('radar_cohort_machine_vectors')['vectors']; cases={v['case_id']:v for v in vectors}
    required=set(EVENTS+['persistent','stock_warm','same_day_revision','multi_sector','focus_exclusion','display_exclusion','retracted','corrected','source_correction','formal_exit_reentry','unknown_evidence','hypothesis_incomplete','risk_after_false','illegal_episode_revision','focus_qualification','fabricated_hypothesis','missing_owner_event'])
    require(set(cases)==required and len(cases)==len(vectors),'B_VECTOR_COVERAGE')
    for event in EVENTS:
        require(cases[event]['expected']==dict(logical_event_count=1,ledger_retained=True,enroll=event!='INVALIDATION',settlement_continues=True),'EVENT_VECTOR_'+event)
    require(cases['persistent']['expected']==dict(logical_event_count=0,new_enrollment_count=0,ledger_retained=True),'PERSISTENT_VECTOR')
    require(cases['stock_warm']['expected']==dict(status='NOT_APPLICABLE',logical_event_count=0,enroll=False),'WARM_VECTOR')
    for cid in ['same_day_revision','multi_sector','focus_exclusion','display_exclusion']:
        require(cases[cid]['expected']==dict(logical_event_id='E1',episode_id='EP1',T0='2026-09-30',enrollment_id='EN1',new_logical_event_count=0 if cid in ['same_day_revision','multi_sector'] else 1,enroll=True,settlement_continues=True),'IDENTITY_VECTOR_'+cid)
    for cid in ['retracted','corrected']:
        require(cases[cid]['expected']==dict(append_observation=True,logical_event_id='E1',enrollment_id='EN1',T0='2026-09-30',controls=['C1'],first_observed_preserved=True,settlement_continues=True),'OBSERVATION_VECTOR')
    checks={'source_correction':dict(T0='2026-09-30',controls=['C1'],enrollment_id='EN1',first_observed_preserved=True,corrected_namespace='CORRECTED'),'formal_exit_reentry':dict(episode_id='EP2',logical_event_id='E2',enrollment_id='EN2',parent_episode_id='EP1'),'unknown_evidence':dict(evidence_quality='UNKNOWN',value=None),'hypothesis_incomplete':dict(status='HYPOTHESIS_SET_INCOMPLETE',hypothesis_count=1),'risk_after_false':dict(risk_stream=True,enroll_new=False,existing_settlement_continues=True)}
    for cid,expected in checks.items():require(cases[cid]['expected']==expected,'B_STATIC_'+cid)
    for cid in ['illegal_episode_revision','focus_qualification','fabricated_hypothesis','missing_owner_event']:require(cases[cid]['expected']=={'reject':True} and cases[cid]['negative'],'B_NEGATIVE_'+cid)
    return dict(R19B_V4_15_RADAR_COHORT_CONTRACT_FREEZE='PASS_LOCAL',RADAR_COHORT_CONTRACT_COMPLETENESS='PASS_LOCAL',V4_15_RUNTIME='NOT_IMPLEMENTED',V4_15_ACCEPTED_HEAD='NOT_CREATED',NEXT='R19D_AFTER_R19B_AND_R19C',vector_count=len(vectors))

def check_c(overrides=None):
    promotion(); get=lambda n:load(n,overrides)
    due=get('due_planner_contract'); path=get('forward_price_path_contract'); bench=get('forward_market_benchmark_contract'); ctl=get('control_assignment_contract')
    require(due['horizons']==[1,3,5,10,20] and due['weekend_holiday_count'] is False and due['endpoint_suspension_shift'] is False and due['same_day_revision_resets_T0'] is False,'SESSION_HORIZONS')
    require(due['calendar']==json.loads((ROOT/'data/v4/V4_DATA_ACCEPTED_HEAD.json').read_bytes())['calendar'],'EXACT_ACCEPTED_MARKET_CALENDAR')
    require(path['formulas']==dict(R_N='P_N/P_0-1',MFE_N='max(0,max(High_j/P_0-1 for j=1..N))',MAE_N='min(0,min(Low_j/P_0-1 for j=1..N))',PATH_MDD_CLOSE_N='min(P_j/max(P_0..P_j)-1 for j=0..N)') and path['common_basis_required'] and path['T0_intraday_extrema_included'] is False and path['evaluation_basis_date']=='T+N','FORMULA_AND_BASIS')
    require(get('outcome_status_contract')['states']==STATES and get('outcome_status_contract')['no_terminal_return'] is None,'OUTCOME_ENUM_NO_ZERO_FILL')
    require(get('competing_outcome_contract')['episode_events']==['CONFIRMED','INVALIDATED','EXPIRED'] and get('competing_outcome_contract')['right_censored_is_event'] is False and get('competing_outcome_contract')['price_settlement_continues'],'COMPETING_OUTCOME')
    rev=get('settlement_revision_contract')
    require(rev['outcome_key']==OKEY and rev['same_source']=='IDEMPOTENT' and rev['corrected_source']=='APPEND_NEW_EVALUATION_REVISION' and rev['overwrite_signal_enrollment'] is False,'OUTCOME_APPEND_ONLY')
    require(bench['marked_estimate']==dict(coverage_gate_value=None,suspension_quote_age_gate_value=None,permission=False,status='CONTRACT_DEFINED_BUT_PERMISSION_BLOCKED_IF_REQUIRED_NUMERIC_GATES_UNSET') and bench['reweight'] is False and bench['consumer_isolation'] and bench['core_market_reference_shared_identity'] is False,'NO_THRESHOLD_INVENTION_NO_REWEIGHT')
    require(bench['constituent_states']==['IDENTITY_UNKNOWN','ADJUSTMENT_UNKNOWN','DELISTED','CONFIRMED_SUSPENSION','DATA_MISSING','ACTUAL_ENDPOINT'] and bench['primary_state_precedence']==bench['constituent_states'],'CONSTITUENT_PRECEDENCE')
    sector=get('forward_sector_benchmark_contract'); rotation=get('rotation_pulse_basket_contract')
    require(sector['exclude_signal_stock'] and sector['minimum_members']==2 and sector['price_extrema']=='CLOSE_ONLY_NO_SUM_OF_MEMBER_INTRADAY_EXTREMA' and rotation['members']=='KNOWN_BEFORE_PULSE' and rotation['reference']=='PULSE_PREVIOUS_ACCEPTED_SESSION_COMMON_BASIS','SECTOR_ROTATION_BOUNDARIES')
    require(ctl['A']['missing']=='NOT_AVAILABLE' and ctl['A']['posthoc_reconstruction'] is False and ctl['B']['order']==['delta3 DESC','security_id ASC'] and ctl['C']['maximum_controls']==3 and ctl['C']['features']==['log(prior20_mean_amount)','vol20','RPS20'] and ctl['future_refill'] is False and ctl['assignments_immutable'] and ctl['A_unavailable_blocks_B_C'] is False,'CONTROLS_FROZEN')
    require(get('settlement_readback_contract')['rewrite_T0'] is False and get('settlement_readback_contract')['selection_independent'],'READBACK_BOUNDARY')
    fields_check(C_NAMES,get('settlement_field_registry')['registry'],overrides)
    registry={f['field_id']:f for f in get('settlement_field_registry')['registry']}
    for name in ['benchmark_id','benchmark_members','initial_weights','fixed_shares','sector_members','pulse_members']:
        require(registry[name]['time_role']=='T0_FROZEN' and registry[name]['revision_behavior']=='IMMUTABLE_T0_SNAPSHOT','T0_SNAPSHOT_FIELD_'+name)
    for name in ['terminal_value','evaluation_comparison_reference']:
        require(registry[name]['type']=='number' and registry[name]['unit']=='CNY_per_share','PRICE_FIELD_TYPE_'+name)
    require(registry['transform_coefficients']['type']=='object' and registry['source_asof']['unit']=='UTC_timestamp','TRANSFORM_METADATA_TYPE')
    vectors=get('settlement_machine_vectors')['vectors']; cases={v['case_id']:v for v in vectors}
    expected_ids=set(['horizon_'+str(n) for n in [1,3,5,10,20]]+['up','down_recover','peak_drop','corporate_action','suspension_endpoint','suspension_interior','unknown_gap','delisted_no_terminal','delisted_terminal','adjustment_mismatch','future_leakage','idempotent','correction','matured_missing','pending','time_to_event_cutoff','competing_same_day','benchmark_missing','benchmark_observed','marked_unset','sector_n1','control_A_missing','control_B_N','control_C_industry','control_C_market','no_future_refill','control_crosses_signal','focus_ui_exclusion','invalidated_still_settles','calendar_holiday','outcome_correction','sector_intraday'])
    require(set(cases)==expected_ids and len(cases)==len(vectors),'C_VECTOR_COVERAGE'); numeric_vectors(vectors)
    static={
        'suspension_endpoint':dict(status='SUSPENDED_AT_HORIZON',R_N=None,shift_horizon=False),
        'suspension_interior':dict(R_N=.1,MFE_N=.15,MAE_N=0,PATH_MDD_CLOSE_N=0,actual_count=1),
        'unknown_gap':dict(path_quality='MATURED_DATA_MISSING',R_N=.1,MFE_N=None,MAE_N=None,PATH_MDD_CLOSE_N=None),
        'delisted_no_terminal':dict(status='DELISTED_BEFORE_HORIZON',R_N=None),
        'delisted_terminal':dict(status='DELISTED_BEFORE_HORIZON',endpoint_quality='OBSERVED_TERMINAL_VALUE',R_N=-.2),
        'adjustment_mismatch':dict(status='ADJUSTMENT_UNKNOWN',R_N=None),
        'future_leakage':dict(reject=True), 'idempotent':dict(new_revision_count=0,idempotent=True),
        'correction':dict(append_revision=True,T0_unchanged=True,first_observed_preserved=True),
        'matured_missing':dict(status='MATURED_DATA_MISSING',right_censored=False,R_N=None),
        'pending':dict(status='PENDING'), 'time_to_event_cutoff':dict(status='RIGHT_CENSORED',competing_event=None),
        'competing_same_day':dict(first_event='INVALIDATED',price_settlement_continues=True),
        'benchmark_missing':dict(weights=[.5,.5],endpoint_coverage=.5,missing_weight=.5,observed_contribution=.55,benchmark_quality='PARTIAL_UNVALUED',relative_market_return=None,absolute_settlement=True),
        'benchmark_observed':dict(R_B=0,benchmark_quality='OBSERVED',reweight=False),
        'marked_unset':dict(marked_relative_permission=False,absolute_settlement=True,invented_threshold=False),
        'sector_n1':dict(relative_sector_return=None,quality='UNKNOWN',absolute_settlement=True),
        'control_A_missing':dict(A='NOT_AVAILABLE',B='INDEPENDENT',C='INDEPENDENT'),
        'control_C_market':dict(scope='MATCH_SCOPE_MARKET',controls=['S1'],count=1),
        'no_future_refill':dict(controls=['S1'],refill=False),
        'control_crosses_signal':dict(ITT_controls=['S1'],append_crossed_signal_at=True),
        'focus_ui_exclusion':dict(settle=True),'invalidated_still_settles':dict(settle=True),
        'outcome_correction':dict(T0_unchanged=True,controls_unchanged=True,first_observed_preserved=True),
        'sector_intraday':dict(reject=True), 'calendar_holiday':dict(due='2026-10-08')}
    for cid,o in static.items():require(cases[cid]['expected']==o,'C_STATIC_'+cid)
    i=cases['control_B_N']['input']; selected=[r[0] for r in sorted(i['candidates'],key=lambda r:(-r[1],r[0]))[:i['N']]]
    require(cases['control_B_N']['expected']==dict(controls=selected,count=2),'CONTROL_B_NUMERIC')
    i=cases['control_C_industry']['input']; distances=sorted([(sum(abs(a-b) for a,b in zip(i['signal_ranks'],r[1])),r[0]) for r in i['candidates']])[:3]
    actual=cases['control_C_industry']['expected']; require(actual['controls']==[r[1] for r in distances] and actual['scope']=='MATCH_SCOPE_INDUSTRY','CONTROL_C_NEAREST')
    for a,b in zip(actual['distances'],[r[0] for r in distances]):require(math.isclose(a,b,abs_tol=1e-12),'CONTROL_C_DISTANCE')
    return dict(R19C_V4_15_SETTLEMENT_CONTRACT_FREEZE='PASS_LOCAL',SETTLEMENT_CONTRACT_COMPLETENESS='PASS_LOCAL',V4_15_RUNTIME='NOT_IMPLEMENTED',V4_15_ACCEPTED_HEAD='NOT_CREATED',NEXT='R19D_AFTER_R19B_AND_R19C',vector_count=len(vectors))

def exact_refs(value):
    import hashlib
    if isinstance(value,list):
        for item in value:exact_refs(item)
    elif isinstance(value,dict):
        if {'path','sha256','bytes'}<=set(value):
            p=(ROOT/value['path']).resolve()
            require(p.is_relative_to(ROOT.resolve()) and '..' not in Path(value['path']).parts,'PACKAGE_PATH_ESCAPE')
            raw=p.read_bytes();require(len(raw)==value['bytes'] and hashlib.sha256(raw).hexdigest()==value['sha256'],'PACKAGE_EXACT_'+value['path'])
        else:
            for item in value.values():exact_refs(item)

def check_d(overrides=None, verify_bindings=True):
    check_b(overrides);check_c(overrides);get=lambda n:load(n,overrides)
    package=get('contract_package')
    names=B_NAMES+C_NAMES+D_NAMES
    require({r['path'] for r in package['contracts']}=={'config/v4_15_'+n+'_v1.json' for n in names} and len(package['contracts'])==len(names),'EXACT_CONTRACT_FILE_SET')
    if verify_bindings:exact_refs(package)
    require(all(package[k] is False for k in ['runtime_implemented','production','shadow','focus','formal_migration']) and package['V4_15_ACCEPTED_HEAD']=='NOT_CREATED' and package['HISTORICAL_PIT_EFFECTIVENESS']=='NOT_GRANTED' and package['NEXT']=='STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT','D_PERMISSION_BOUNDARY')
    stage=json.loads((ROOT/'data/v4/V4_STAGE_ACCEPTED_HEAD.json').read_bytes()); data=json.loads((ROOT/'data/v4/V4_DATA_ACCEPTED_HEAD.json').read_bytes())
    require(package['owner_heads']=={k:stage['v4_'+k+'_binding'] for k in ['07','08','09','10','11','12','13','14']},'EXACT_OWNER_HEADS')
    source_paths={r['path'] for r in package['source_authorities']}
    require(source_paths=={'data/v4/V4_14_ACCEPTED_HEAD.json','data/v4/V4_DATA_ACCEPTED_HEAD.json',data['calendar']['path'],data['identity']['path'],'data/v4/V4_01_ACCEPTED_HEAD.json','data/v4/V4_08_PIT_MEMBERSHIP_ACCEPTED_HEAD_R1.json','config/v4_official_exchange_calendar_v2.json','config/v4_capability_cutover_policy_v1.json','config/v4_02_go_forward_pit_adjustment_r2.json'},'SOURCE_AUTHORITY_SET')
    b=get('radar_cohort_field_registry')['registry'];c=get('settlement_field_registry')['registry'];union=get('field_registry')['registry']
    require(union==b+c and len(union)==len({f['field_id'] for f in union}),'UNION_AUTHORITY_P0')
    dag=get('dag_registry')
    require(dag['nodes']==NODES and [(e['source'],e['target']) for e in dag['edges']]==list(zip(NODES,NODES[1:])),'EXACT_DAG_ACYCLIC')
    require([[e['source'],e['target']] for e in dag['non_edges']]==NONEDGES and all(e['status']=='FORBIDDEN' for e in dag['non_edges']),'NON_EDGES')
    require(dag['accepted_owner_feedback'] is False,'NO_OWNER_FEEDBACK')
    caps=get('source_capability_matrix');require([r['capability'] for r in caps['capabilities']]==CAPS and caps['independent_degradation'] and caps['raw_provider_fallback'] is False and caps['HISTORICAL_PIT_EFFECTIVENESS']=='NOT_GRANTED','INDEPENDENT_CAPABILITY_MATRIX')
    for row in caps['capabilities']:require(row['required_sources'] and row['degradation'] and all(row[k] is False for k in ['runtime_permission','production','shadow','focus']),'CAPABILITY_PERMISSION')
    quality=get('quality_degradation')
    require(quality['marked_coverage_gate'] is None and quality['marked_quote_age_gate'] is None and quality['outcome_states']==STATES and quality['unknown_never_false_or_zero'],'QUALITY_GATES_UNSET')
    expected_rules=[('SECTOR_BENCHMARK_UNAVAILABLE',['SECTOR_RELATIVE_SETTLEMENT'],['ABSOLUTE_FORWARD_SETTLEMENT','MARKET_RELATIVE_SETTLEMENT']),('MARKET_BENCHMARK_PARTIAL',['MARKET_RELATIVE_SETTLEMENT'],['ABSOLUTE_FORWARD_SETTLEMENT','CONTROL_B_DELTA3','CONTROL_C_MATCHED']),('CONTROL_A_MISSING',['CONTROL_A_LEGACY'],['CONTROL_B_DELTA3','CONTROL_C_MATCHED']),('MARKED_ESTIMATE_GATES_UNSET',['MARKED_RELATIVE_OUTPUT'],['ABSOLUTE_FORWARD_SETTLEMENT','OBSERVED_RELATIVE_OUTPUT']),('STOCK_WARM_OWNER_ABSENT',['STOCK_UPGRADE_TO_WARM'],['STOCK_PREWATCH','STOCK_CONFIRMED','SECTOR_STAGE']),('INTERIOR_UNKNOWN_GAP',['PATH_EXTREMA','PATH_MDD'],['VERIFIED_ENDPOINT_RETURN'])]
    require(quality['rules']==[dict(reason=r,affected=a,unaffected=u) for r,a,u in expected_rules],'CAPABILITY_ISOLATION_RULES')
    storage=get('storage_schema_design');require(storage['migration_apply'] is False and storage['design_only'],'STORAGE_DESIGN_ONLY')
    keys={'radar_daily_ledger':LKEY,'logical_events':EKEY,'event_observations':['logical_event_id','publication_id'],'enrollment':['enrollment_id'],'controls':['control_assignment_id'],'benchmark_snapshots':['benchmark_id'],'due_items':['enrollment_id','horizon'],'settlement_revisions':OKEY,'competing_outcomes':['enrollment_id','competing_event','competing_source_publication'],'control_crossing_observations':['control_assignment_id','crossed_signal_at','publication_id']}
    tables={t['table']:t for t in storage['tables']};require(set(tables)==set(keys),'STORAGE_TABLE_COVERAGE')
    fields={f['field_id'] for f in union}
    fk_expected={'event_observations':('logical_events',['logical_event_id']), 'enrollment':('logical_events',['logical_event_id']), 'controls':('enrollment',['enrollment_id']), 'benchmark_snapshots':('enrollment',['enrollment_id']), 'due_items':('enrollment',['enrollment_id']), 'settlement_revisions':('due_items',['enrollment_id','horizon']), 'competing_outcomes':('enrollment',['enrollment_id']), 'control_crossing_observations':('controls',['control_assignment_id'])}
    for name,t in tables.items():
        require(t['primary_key']==keys[name] and set(t['columns'])<=fields and set(t['primary_key'])<=set(t['columns']) and t['immutable_columns']==t['columns'] and t['append_only'] and t['publication_date_consistency'] and t['source_digest_binding'],'STORAGE_IDENTITY_'+name)
        if name in fk_expected:
            target,cols=fk_expected[name];require(t['foreign_keys']==[dict(columns=cols,target_table=target,target_columns=cols)],'STORAGE_FK_'+name)
        else:require(t['foreign_keys']==[],'UNEXPECTED_STORAGE_FK')
    require(tables['logical_events']['unique_keys']==[['logical_event_id']] and tables['enrollment']['unique_keys']==[['logical_event_id','cohort_namespace']],'STORAGE_LOGICAL_UNIQUENESS')
    vectors=get('machine_vectors')['cross_family_vectors'];cases={v['case_id']:v for v in vectors}
    expected={'radar_enrollment_identity':dict(logical_event_id='E1',enrollment_id='EN1',T0='2026-09-30'),'persistent_no_duplicate':dict(new_event_count=0,new_enrollment_count=0),'same_day_revision':dict(logical_event_id='E1',append_observation=True,episode_id='EP1'),'invalidated_forward':dict(settle=True),'focus_excluded':dict(enroll=True,settle=True),'display_excluded':dict(enroll=True,settle=True),'source_correction':dict(first_observed_preserved=True,T0_unchanged=True,controls_unchanged=True),'outcome_correction':dict(T0_unchanged=True,append_revision=True),'market_missing_absolute':dict(absolute=True,market_relative=False),'sector_unavailable':dict(absolute=True,sector_relative=False),'control_A_missing':dict(A='NOT_AVAILABLE',B=True,C=True),'marked_gates_unset':dict(coverage_gate=None,quote_age_gate=None,marked_permission=False,absolute=True),'FEP_no_dependency':dict(reject=True)}
    require(len(cases)==len(vectors) and set(cases)==set(expected),'CROSS_FAMILY_VECTOR_COVERAGE')
    for cid,out in expected.items():require(cases[cid]['input'] and cases[cid]['expected']==out,'CROSS_FAMILY_'+cid)
    # This round must leave every previously tracked source/contract/replay byte intact.
    import subprocess
    changed=subprocess.check_output(['git','diff','f4ad7d632e53734798c064f011e2b53ecd99bc27','--name-only','--','src','config','reports/v4_14_replay_r18','scripts/v4_14_rollback_oracle.py','scripts/v4_14_consumption_oracle_r18r1r1.py'],cwd=ROOT,text=True).splitlines()
    require(all(p.startswith('config/v4_15_') or p=='config/v4_14_accepted_entry_contract_v1.json' for p in changed),'FROZEN_BUSINESS_AND_REPLAY_UNCHANGED')
    return dict(R19D_V4_15_CONTRACT_INTEGRATION='PASS_LOCAL',V4_15_CONTRACT_COMPLETENESS='PASS_READY_FOR_EXTERNAL_AUDIT',V4_15_RUNTIME='NOT_IMPLEMENTED',V4_15_ACCEPTED_HEAD='NOT_CREATED',V4_STAGE_ACCEPTED_HEAD='V4_00_TO_V4_14_ACCEPTED',V4_DATA_ACCEPTED_HEAD='2026-09-30',Production=False,Shadow=False,Focus=False,NEXT='STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT',contract_count=len(names),field_count=len(union),cross_vector_count=len(vectors),checks={k:'PASS' for k in ['exact_contract_file_set','exact_accepted_sources_and_owner_heads','independent_required_field_schema','unique_field_authority','event_ledger_observation_enrollment_identity','common_basis_horizon_formulas','outcome_and_constituent_quality_states','DAG_and_forbidden_non_edges','independent_capability_degradation','marked_numeric_gates_remain_unset','static_and_independent_numerical_vectors','storage_keys_foreign_keys_immutability','cross_family_expectations','frozen_business_replay_consumption_rollback_unchanged','runtime_and_permission_boundary']})

if __name__=='__main__':
    import sys
    from scripts.r19_io import atomic
    stage=sys.argv[1]; result={'B':check_b,'C':check_c,'D':check_d}[stage]()
    atomic('reports/r19'+stage.lower()+('/V4_15_STAGE_ENTRY_GATE.json' if stage=='D' else '/CONTRACT_GATE.json'),result)
    print(json.dumps(result))
