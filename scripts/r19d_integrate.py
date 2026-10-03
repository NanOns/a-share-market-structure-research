"""Integrate already-gated contract families; design artifacts only."""
from scripts.r19_io import BASE, read, ref, atomic
from scripts.r19_freeze_contracts import contract, MASTER, LEDGER, EVENT, OBS, OUTCOME

B=['radar_contract','radar_event_registry','why_now_schema','conflict_hypothesis_schema','cohort_contract','cohort_revision_policy','radar_cohort_field_registry','radar_cohort_machine_vectors']
C=['due_planner_contract','forward_price_path_contract','outcome_status_contract','competing_outcome_contract','forward_market_benchmark_contract','forward_sector_benchmark_contract','rotation_pulse_basket_contract','control_assignment_contract','settlement_revision_contract','settlement_readback_contract','settlement_field_registry','settlement_machine_vectors']

def integrate():
    assert read('reports/r19b/CONTRACT_GATE.json')['RADAR_COHORT_CONTRACT_COMPLETENESS']=='PASS_LOCAL'
    assert read('reports/r19c/CONTRACT_GATE.json')['SETTLEMENT_CONTRACT_COMPLETENESS']=='PASS_LOCAL'
    union=read('config/v4_15_radar_cohort_field_registry_v1.json')['registry']+read('config/v4_15_settlement_field_registry_v1.json')['registry']
    assert len({f['field_id'] for f in union})==len(union)
    contract('field_registry','V4_15_FIELDS_V1',['87A'],[],registry=union, union_sources=[ref('config/v4_15_radar_cohort_field_registry_v1.json'),ref('config/v4_15_settlement_field_registry_v1.json')],duplicate_authority_severity='P0')
    nodes=['Accepted V4-14 publication','Radar event projection','complete daily ledger','logical event / observation','first ASSERTED enrollment','frozen benchmark + controls','due planner','future accepted source readback','settlement / outcome revision','readback / statistics consumers']
    edges=[dict(source=a,target=b,time_rule='ACCEPTED_AVAILABLE_AT_BEFORE_CONSUMPTION; T0_INPUTS_CUTOFF_LE_T0; FUTURE_PRICE_ONLY_IN_SETTLEMENT') for a,b in zip(nodes,nodes[1:])]
    nonedges=[dict(source=a,target=b,status='FORBIDDEN') for a,b in [['Focus','enrollment'],['UI Top-K','enrollment'],['Forward outcome','T0 state'],['FEP prediction','Core/Radar'],['Corrected outcome','T0'],['future source','same-day decision']]]
    contract('dag_registry','V4_15_DAG_V1',['3','13','45A','46','54'],[],nodes=nodes,edges=edges,non_edges=nonedges,source_temporal_rule='max_source_trade_date<=target_trade_date AND source_asof<=cutoff AND available_at<=decision_time; membership effective_time AND available_time required; settlement source available_at<=evaluation/readback_asof', accepted_owner_feedback=False)
    cap_rules={
        'RADAR_EVENT_PROJECTION':('ACCEPTED_V4_14_OWNER_PUBLICATIONS','ONLY_SUPPORTED_OWNER_EVENT_FAMILIES; STOCK_WARM_NOT_APPLICABLE'),
        'VALIDATION_COHORT':('ACCEPTED_V4_14_LOGICAL_EVENTS_AND_OBSERVATION_SLOT','ALL_ELIGIBLE; NO_FOCUS_UI_FILTER; LATE_SLOT_RECONSTRUCTED'),
        'ABSOLUTE_FORWARD_SETTLEMENT':('ACCEPTED_IDENTITY_CALENDAR_LOCAL_ADJUSTMENT_AND_ENDPOINT','INDEPENDENT_FROM_BENCHMARK_CONTROLS; UNKNOWN_GAPS_DEGRADE_PATH_ONLY'),
        'MARKET_RELATIVE_SETTLEMENT':('T0_FIXED_MARKET_BASKET_AND_VERIFIED_ENDPOINTS','OBSERVED_ONLY_IF_ALL_CONSTITUENTS_QUALIFIED; MARKED_BLOCKED_UNSET_NUMERIC_GATES'),
        'SECTOR_RELATIVE_SETTLEMENT':('T0_PIT_TARGET_EXCLUDED_MEMBERS_AND_VERIFIED_ENDPOINTS','N_LT_2_UNKNOWN; DOES_NOT_BLOCK_ABSOLUTE'),
        'CONTROL_A_LEGACY':('ACTUAL_T0_LEGACY_OUTPUT','NOT_AVAILABLE_IF_NO_OUTPUT; B_C_INDEPENDENT'),
        'CONTROL_B_DELTA3':('T0_HARD_SAFETY_DELTA3_AND_EVENT_COUNTS','STABLE_SECURITY_ID; ACTUAL_SHORT_POOL_NO_FUTURE_REFILL'),
        'CONTROL_C_MATCHED':('T0_KNOWN_INDUSTRY_AND_HARD_SAFETY_FEATURE_RANKS','MARKET_SCOPE_IF_INDUSTRY_UNAVAILABLE; ITT_FIXED'),
        'COMPETING_OUTCOMES':('ACCEPTED_STATE_REDUCER_EPISODE_EVENT_PUBLICATIONS','OBSERVATION_CENSORING_SEPARATE; PRICE_COLLECTION_CONTINUES'),
        'OUTCOME_REVISION_READBACK':('IMMUTABLE_EVALUATION_REVISIONS_AVAILABLE_AT','FIRST_OBSERVED_LATEST_CORRECTED_SEPARATE_NO_T0_REWRITE')}
    contract('source_capability_matrix','V4_15_CAPABILITIES_V1',['52B','45','46','49A','49B'],[],capabilities=[dict(capability=k,required_sources=v[0],degradation=v[1],contract_defined=True,runtime_permission=False,production=False,shadow=False,focus=False) for k,v in cap_rules.items()], independent_degradation=True,HISTORICAL_PIT_EFFECTIVENESS='NOT_GRANTED', raw_provider_fallback=False)
    contract('quality_degradation','V4_15_QUALITY_V1',['8','47','49A','52B'],[],quality_states=['KNOWN','UNKNOWN','NOT_APPLICABLE','NOT_IMPLEMENTED','DEGRADED'],outcome_states=read('config/v4_15_outcome_status_contract_v1.json')['states'],benchmark_states=['OBSERVED','MARKED_ESTIMATE','PARTIAL_UNVALUED'],rules=[dict(reason=r,affected=a,unaffected=u) for r,a,u in [('SECTOR_BENCHMARK_UNAVAILABLE',['SECTOR_RELATIVE_SETTLEMENT'],['ABSOLUTE_FORWARD_SETTLEMENT','MARKET_RELATIVE_SETTLEMENT']),('MARKET_BENCHMARK_PARTIAL',['MARKET_RELATIVE_SETTLEMENT'],['ABSOLUTE_FORWARD_SETTLEMENT','CONTROL_B_DELTA3','CONTROL_C_MATCHED']),('CONTROL_A_MISSING',['CONTROL_A_LEGACY'],['CONTROL_B_DELTA3','CONTROL_C_MATCHED']),('MARKED_ESTIMATE_GATES_UNSET',['MARKED_RELATIVE_OUTPUT'],['ABSOLUTE_FORWARD_SETTLEMENT','OBSERVED_RELATIVE_OUTPUT']),('STOCK_WARM_OWNER_ABSENT',['STOCK_UPGRADE_TO_WARM'],['STOCK_PREWATCH','STOCK_CONFIRMED','SECTOR_STAGE']),('INTERIOR_UNKNOWN_GAP',['PATH_EXTREMA','PATH_MDD'],['VERIFIED_ENDPOINT_RETURN'])]],unknown_never_false_or_zero=True,capability_combination='INTERSECTION_OF_AFFECTED_PERMISSIONS_NO_GLOBAL_OVERWRITE',marked_coverage_gate=None,marked_quote_age_gate=None)
    schemas={
        'radar_daily_ledger':(LEDGER,['trade_date','eligibility_state','priority_bucket','publication_digest'],[]),
        'logical_events':(EVENT,['logical_event_id'],[]),
        'event_observations':(OBS,['observation_state','source_correction','supersedes_observation'],[dict(columns=['logical_event_id'],target_table='logical_events',target_columns=['logical_event_id'])]),
        'enrollment':(['enrollment_id'],['logical_event_id','cohort_namespace','T0','calendar_identity','adjustment_identity','source_publication','source_digest','parameter_digest','contract_digest','signal_reference','comparison_reference','benchmark_ids','control_assignment_ids','evidence_class','observation_slot'],[dict(columns=['logical_event_id'],target_table='logical_events',target_columns=['logical_event_id'])]),
        'controls':(['control_assignment_id'],['enrollment_id','control_type','control_entity_ids','control_feature_snapshot','assignment_digest','match_scope'],[dict(columns=['enrollment_id'],target_table='enrollment',target_columns=['enrollment_id'])]),
        'benchmark_snapshots':(['benchmark_id'],['enrollment_id','benchmark_members','initial_weights','fixed_shares','adjustment_identity','benchmark_constituent_policy'],[dict(columns=['enrollment_id'],target_table='enrollment',target_columns=['enrollment_id'])]),
        'due_items':(['enrollment_id','horizon'],['due_trade_date','calendar_identity'],[dict(columns=['enrollment_id'],target_table='enrollment',target_columns=['enrollment_id'])]),
        'settlement_revisions':(OUTCOME,['outcome_id','evaluation_revision','supersedes','available_at','evaluation_source_identity','evidence_class','reason_codes','outcome_status','R_N','MFE_N','MAE_N','PATH_MDD_CLOSE_N','evaluation_basis_date','evaluation_comparison_reference','evaluation_adjustment_identity','transform_coefficients','transform_digest','price_path'],[dict(columns=['enrollment_id','horizon'],target_table='due_items',target_columns=['enrollment_id','horizon'])]),
        'competing_outcomes':(['enrollment_id','competing_event','competing_source_publication'],['first_event_trade_date','censoring_state'],[dict(columns=['enrollment_id'],target_table='enrollment',target_columns=['enrollment_id'])]),
        'control_crossing_observations':(['control_assignment_id','crossed_signal_at','publication_id'],['publication_digest'],[dict(columns=['control_assignment_id'],target_table='controls',target_columns=['control_assignment_id'])])}
    tables=[]
    for name,(pk,extra,fks) in schemas.items():
        columns=list(dict.fromkeys(pk+extra)); tables.append(dict(table=name,primary_key=pk,unique_keys=[['logical_event_id']] if name=='logical_events' else [['logical_event_id','cohort_namespace']] if name=='enrollment' else [],columns=columns,foreign_keys=fks,immutable_columns=columns,append_only=True,revision_rule='INSERT_ONLY; SAME_SOURCE_IDEMPOTENT; CORRECTIONS_SUPERSEDE_WITHOUT_UPDATE_OR_DELETE',publication_date_consistency='PUBLICATION_TRADE_DATE_MATCHES_LEDGER_OR_EVENT; T0_EQUALS_FIRST_ASSERTED_EVENT_MARKET_DATE; EVALUATION_BASIS_EQUALS_DUE_DATE',source_digest_binding='EXACT_ACCEPTED_PUBLICATION_OR_EVALUATION_DIGEST; NO_LATEST_SCAN'))
    contract('storage_schema_design','V4_15_STORAGE_DESIGN_V1',['45A','46','77B'],[],tables=tables,readback_indexes=[['due_items','due_trade_date','enrollment_id','horizon'],['settlement_revisions','enrollment_id','horizon','available_at','evaluation_revision'],['event_observations','logical_event_id','publication_id']],referential_rules=['ENROLLMENT_BENCHMARK_IDS_RESOLVE_EXACT_SNAPSHOT','ENROLLMENT_CONTROL_ASSIGNMENT_IDS_RESOLVE_EXACT_ASSIGNMENT','SUPERSEDES_SAME_ENROLLMENT_HORIZON_CONTRACT_ONLY','PUBLICATION_ID_BINDS_EXACT_DIGEST_DATE','FIRST_ASSERTED_SLOT_FIRST_OBSERVED_ONLY'],migration_apply=False,design_only=True)
    cross=[]
    expected={
        'radar_enrollment_identity':dict(logical_event_id='E1',enrollment_id='EN1',T0='2026-09-30'),
        'persistent_no_duplicate':dict(new_event_count=0,new_enrollment_count=0),
        'same_day_revision':dict(logical_event_id='E1',append_observation=True,episode_id='EP1'),
        'invalidated_forward':dict(settle=True), 'focus_excluded':dict(enroll=True,settle=True), 'display_excluded':dict(enroll=True,settle=True),
        'source_correction':dict(first_observed_preserved=True,T0_unchanged=True,controls_unchanged=True),
        'outcome_correction':dict(T0_unchanged=True,append_revision=True),
        'market_missing_absolute':dict(absolute=True,market_relative=False),
        'sector_unavailable':dict(absolute=True,sector_relative=False),
        'control_A_missing':dict(A='NOT_AVAILABLE',B=True,C=True),
        'marked_gates_unset':dict(coverage_gate=None,quote_age_gate=None,marked_permission=False,absolute=True),
        'FEP_no_dependency':dict(reject=True)}
    inputs={'radar_enrollment_identity':dict(event='FIRST_PREWATCH',eligible=True,first_asserted=True), 'persistent_no_duplicate':dict(event='PERSISTENT'), 'same_day_revision':dict(event='FIRST_PREWATCH',revision='r2'), 'invalidated_forward':dict(state='INVALIDATED',enrollment='EN1'), 'focus_excluded':dict(focus=False,eligible=True), 'display_excluded':dict(displayed=False,eligible=True), 'source_correction':dict(source_correction=True), 'outcome_correction':dict(evaluation_source_changed=True), 'market_missing_absolute':dict(market_member_missing=True,absolute_endpoint_verified=True), 'sector_unavailable':dict(sector_members=1,absolute_endpoint_verified=True), 'control_A_missing':dict(legacy_output=None), 'marked_gates_unset':dict(policy_coverage=None,policy_quote_age=None), 'FEP_no_dependency':dict(proposed_edge=['FEP prediction','Core/Radar'])}
    for cid,out in expected.items():cross.append(dict(case_id=cid,input=inputs[cid],expected=out,negative=cid=='FEP_no_dependency'))
    contract('machine_vectors','V4_15_INTEGRATED_VECTORS_V1',['45A','46','49A','54'],[],family_vectors=[ref('config/v4_15_radar_cohort_machine_vectors_v1.json'),ref('config/v4_15_settlement_machine_vectors_v1.json')],cross_family_vectors=cross,expected_authority='STATIC_CONTRACT_EXPECTATIONS_NOT_RUNTIME_GENERATED')
    allnames=B+C+['field_registry','dag_registry','source_capability_matrix','quality_degradation','storage_schema_design','machine_vectors']
    data=read('data/v4/V4_DATA_ACCEPTED_HEAD.json'); stage=read('data/v4/V4_STAGE_ACCEPTED_HEAD.json')
    authorities={k:stage['v4_'+k+'_binding'] for k in ['07','08','09','10','11','12','13','14']}
    sources=[ref('data/v4/V4_14_ACCEPTED_HEAD.json'),ref('data/v4/V4_DATA_ACCEPTED_HEAD.json'),data['calendar'],data['identity'],ref('data/v4/V4_01_ACCEPTED_HEAD.json'),ref('data/v4/V4_08_PIT_MEMBERSHIP_ACCEPTED_HEAD_R1.json'),ref('config/v4_official_exchange_calendar_v2.json'),ref('config/v4_capability_cutover_policy_v1.json'),ref('config/v4_02_go_forward_pit_adjustment_r2.json')]
    package=dict(contract_id='V4_15_CONTRACT_PACKAGE_V1',version='1.0.0',input_commit=BASE,design_authority=dict(**ref(MASTER),sections=['3','13','36','39','40','41','41G','43','44','45','45A','46','46A','47','48','49','49A','49B','51A.1','52B','54','58','77B','78','81','87A']),contracts=[ref('config/v4_15_'+n+'_v1.json') for n in allnames],source_authorities=sources,owner_heads=authorities,promotion_gate=ref('reports/r19a/PROMOTION_GATE.json'),family_gates=[ref('reports/r19b/CONTRACT_GATE.json'),ref('reports/r19c/CONTRACT_GATE.json')],runtime_implemented=False,V4_15_ACCEPTED_HEAD='NOT_CREATED',production=False,shadow=False,focus=False,formal_migration=False,HISTORICAL_PIT_EFFECTIVENESS='NOT_GRANTED',NEXT='STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT')
    atomic('config/v4_15_contract_package_v1.json',package)

if __name__=='__main__':integrate()
