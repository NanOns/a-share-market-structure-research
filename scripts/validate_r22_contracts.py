"""Independent design-completeness oracle; never imports builder or runtime helpers."""
import json
from pathlib import Path
from scripts.r22_io import ROOT,BASE,HEAD,CONFIG,ACCEPT,ARCH,R21_AUDIT,read,ref,baseline
from scripts.validate_pre16_governance import require,exact
from scripts.validate_pre16_finalization import validate as formalization

NAMES=['realtime_shadow','observation_slot','shadow_namespace','shadow_health','settlement_worker','machine_vectors']
CAPS=['STOCK_CORE','STOCK_SECTOR_DEPENDENT','SECTOR_STAGE','ROTATION','SECTOR_RISK_CHANGE']
SLOT_FIELDS=['trade_date','model_contract_id','parameter_set_id','state_lineage_id','execution_mode','namespace','scheduled_cutoff_at','observation_deadline','source_provider_available_at','system_available_at','computation_started_at','computation_finished_at','accepted_at','slot_status','publication_id','core_revision','source_manifest_digest','capability_scope']
HEALTH_FIELDS=['status','capability_scope','trade_date','model_contract_id','parameter_digest','slot_status','source_quality','publication_status','temporal_leakage_status','duplicate_episode_status','state_integrity_status','P0_violations','settlement_backlog']

def verify_vectors(v):
    # Literal independently specified policy expectations, not evaluator outputs.
    expected={
      'ON_TIME_FIRST_SLOT':{'classification':'PIT_OBSERVED','original_enrollments':1,'namespace':'SHADOW_V4'},
      'LATE_BACKFILL':{'slot':'MISSED_OBSERVATION_SLOT','classification':'RECONSTRUCTED_ASOF','original_enrollments':0},
      'SAME_DAY_R2':{'append_observation':True,'new_original_enrollments':0,'preserve_T0':True},
      'LEGACY_PRIOR':{'reject':'NAMESPACE_PRIOR_MISMATCH'},
      'MISSING_PREVIOUS_SHADOW_SESSION':{'status':'GAP_FAIL_CLOSED','skip_day_yesterday':False},
      'MODEL_PARAMETER_CHANGE':{'new_lineage':True,'reset_affected_window':True,'old_observations_immutable':True},
      'HISTORICAL_REPLAY':{'real_shadow_session_increment':0,'original_realtime_enrollments':0},
      'FOCUS_UI_EXCLUSION':{'eligible_enrollment_unchanged':True,'settlement_continues':True},
      'PRE_DUE_ENDPOINT':{'reject':'FUTURE_SOURCE_READ_BEFORE_DUE','future_read_count':0},
      'DUE_SOURCE_UNAVAILABLE':{'status':'PENDING_DUE_SOURCE_UNAVAILABLE','return_value':None,'explicit_reason':True},
      'SETTLEMENT_RERUN':{'new_result_revisions':0,'idempotent':True},
      'CORRECTED_EVALUATION_SOURCE':{'append_result_revision':True,'first_observed_unchanged':True},
      'CURRENT_MEMBERSHIP_BACKFILL':{'PIT_OBSERVED':False,'diagnostic_or_reconstructed':True},
      'BAOSTOCK_UNAVAILABLE':{'pure_core_continues':True,'enrichment':'UNKNOWN'},
      'CAPABILITY_ISOLATION':{'A':'BLOCKED_AFFECTED_SCOPE','B':'INDEPENDENTLY_TESTABLE'},
      'P0_STATE_VIOLATION':{'affected_window_reset':True,'stable_pass':False},
      'MISSED_MARKET_SESSION':{'consecutive_streak':0,'real_session_increment':0},
      'LEGACY_PRODUCTION_ISOLATION':{'legacy_writes':0,'legacy_focus_changed':False,'legacy_default_UI_changed':False},
      'SOURCE_CORRECTION_AFTER_ENROLLMENT':{'T0_unchanged':True,'controls_unchanged':True,'benchmark_unchanged':True,'append_only':True},
      'DUPLICATE_LOGICAL_EPISODE':{'status':'P0_FAIL','stable_pass':False},
      'UNSET_CLOCK_AUTHORITY':{'status':'BLOCKED_AFFECTED_SCOPE','PIT_OBSERVED':False,'original_realtime_enrollments':0},
      'GOVERNANCE_CAPABILITY_DEBT':{'contract_entry_blocked':False,'affected_PREWATCH_shadow_active':False},
      'ENGINEERING_MATURITY_VECTOR':{'real_maturity_increment':0,'historical_PIT_granted':False}}
    require(v['evidence_class']=='ENGINEERING_DESIGN_EXPECTATIONS_ONLY_NOT_REAL_OBSERVATIONS' and v['future_runtime_helpers_used'] is False,'INDEPENDENT_ENGINEERING_ONLY_VECTORS')
    rows=v['vectors'];require(len(rows)==len(expected) and {r['scenario'] for r in rows}==set(expected),'COMPLETE_VECTOR_FAMILIES')
    require(len({r['vector_id'] for r in rows})==len(rows),'UNIQUE_VECTOR_IDENTITY')
    for row in rows:
        require(row['inputs'] and row['expected']==expected[row['scenario']] and row['actual_runtime_executed'] is False,'FROZEN_VECTOR_EXPECTATION_'+row['scenario'])
    first=next(r for r in rows if r['scenario']=='ON_TIME_FIRST_SLOT')
    require(first['inputs']==dict(authorized_future_runtime=True,accepted_clock_fixture=True,exact_previous_shadow_session=True,source_visible_by_cutoff=True,accepted_before_deadline=True),'CONDITIONAL_OBSERVED_VECTOR_NOT_CURRENT_AUTHORITY')
    return len(rows)

def verify_semantics(d,root=ROOT):
    for name,c in d.items():
        require(c['contract_id']==('v4_16_'+name+'_contract_v1').upper() if name!='machine_vectors' else c['contract_id']=='V4_16_MACHINE_VECTORS_V1','EXACT_CONTRACT_ID_'+name)
        # Namespace contract naming is SHADOW_NAMESPACE; uniform suffix remains explicit.
        require(c['version']=='1.0.0' and c['execution_baseline']==BASE,'EXACT_CONTRACT_VERSION_'+name)
        require(c['accepted_predecessor']==ref('data/v4/V4_15_ACCEPTED_HEAD.json',root),'EXACT_ACCEPTED_V15_'+name)
        for key in ['model_parameter_identity','source_authority','time_semantics','namespace','PIT_rules','UNKNOWN_degradation','idempotency','revision_behavior','negative_vectors','acceptance_criteria']:require(c.get(key),'MANDATORY_CONTRACT_FIELD_'+key)
        require(all(c[k] is False for k in ['production','shadow','focus','V4_16','runtime_implemented','runtime_authorized']) and c['REAL_SHADOW_OBSERVATIONS']==0,'CONTRACT_NOT_RUNTIME_GRANT_'+name)
        require(all(c[k]=='NOT_GRANTED' for k in ['SHADOW_STABLE','PROVISIONAL_FORWARD_EVIDENCE','FORWARD_SUPPORTED']),'NO_EVIDENCE_GATE_OVERCLAIM_'+name)
        require(c['time_semantics']['timezone']=='Asia/Shanghai' and c['time_semantics']['timestamp_storage']=='UTC_RFC3339','UTC_MARKET_TIME_SEMANTICS')
        require(c['namespace']=='SHADOW_V4' and c['PIT_rules']['reconstruction_cannot_upgrade'] is True,'NO_RECONSTRUCTION_UPGRADE')
        require(c['revision_behavior']=='APPEND_ONLY; ORIGINAL_IDENTITIES_AND_FROZEN_T0_IMMUTABLE' and c['UNKNOWN_degradation']=='FAIL_CLOSED_AFFECTED_CAPABILITY; UNKNOWN_HARD_REQUIREMENT_NEVER_PASSES','APPEND_ONLY_FAIL_CLOSED_COMMON')
        require(c['model_parameter_identity']==dict(model_contract_id='DIGEST_CODE_AST_PARAMETERS_SOURCE_SEMANTICS',parameter_set_id='EXACT_ACCEPTED_PARAMETER_SET',change='NEW_MODEL_ID_AND_AFFECTED_LINEAGE_BOUNDARY'),'FROZEN_MODEL_PARAMETER_BOUNDARY')
        for b in c['source_authority'].values():exact(b,root)
        for key,path in [('audit_head',HEAD),('audit_config',CONFIG),('governance_acceptance',ACCEPT),('v15','data/v4/V4_15_ACCEPTED_HEAD.json'),('stage','data/v4/V4_STAGE_ACCEPTED_HEAD.json'),('data','data/v4/V4_DATA_ACCEPTED_HEAD.json'),('architecture',ARCH)]:require(c['source_authority'].get(key)==ref(path,root),'EXACT_CURRENT_SOURCE_BINDING_'+key)
    slot=d['observation_slot'];clock=slot['clock_authority']
    require(slot['slot_key']==['model_contract_id','state_lineage_id','trade_date'] and slot['fields']==SLOT_FIELDS,'EXACT_OBSERVATION_SLOT')
    require(clock['status']=='BLOCKED_AFFECTED_SCOPE' and clock['scheduled_cutoff_at'] is clock['observation_deadline'] is clock['accepted_clock_binding'] is None,'NO_INVENTED_ACCEPTED_CLOCK')
    require(slot['no_clock']=='BLOCK_REALTIME_ENROLLMENT_NO_PIT_CLAIM' and slot['original_samples_per_slot']==1 and slot['reset_observation_start'] is False,'FAIL_CLOSED_ORIGINAL_SLOT')
    require(slot['first_original_rule']=='FIRST_COMPLIANT_ACCEPTED_PUBLICATION_WITHIN_ACCEPTED_DEADLINE_ONLY' and slot['late_missing']=='MISSED_OBSERVATION_SLOT; LATER_BACKFILL_RECONSTRUCTED_ONLY','FIRST_ON_TIME_ONLY')
    require('accepted_at <= observation_deadline' in slot['visibility_order'][-1] and 'system_available_at <= scheduled_cutoff_at' in slot['visibility_order'],'SOURCE_VISIBILITY_CUTOFF')
    exact(clock['repair_requirement'],root)
    ns=d['shadow_namespace']
    require(ns['read_namespace']==ns['write_namespace']=='SHADOW_V4' and ns['legacy_namespace']=='PRODUCTION_LEGACY' and ns['legacy_writes'] is ns['legacy_prior_reads'] is False,'LEGACY_NAMESPACE_ISOLATION')
    require(ns['prior_rule']=='EXACT_PREVIOUS_MARKET_SESSION_ACCEPTED_SHADOW_HEAD; SAME_PREDECESSOR_ALL_SAME_DAY_REVISIONS' and 'NO_SKIP_DAY_YESTERDAY' in ns['missing_prior'],'EXACT_SHADOW_PRIOR_OR_GAP')
    require(ns['legacy_production_continues'] is True and ns['production_focus_changes'] is ns['default_UI_changes'] is False,'LEGACY_UI_FOCUS_KEEP')
    require(ns['acceptance_transaction']==['STAGING_INVISIBLE','QUALITY_IDENTITY_COVERAGE_CHECK','CONSUMED_MANIFEST_COHORT_OUTBOX_ATOMIC_WRITE','ACCEPTED_HEAD_CAS','COMMIT_VISIBLE'],'ATOMIC_ACCEPTANCE_AND_OUTBOX')
    require(ns['rollback']['formal_DB_migration_apply'] is False and ns['rollback']['drill_required_before_stable'] is True and 'pending_settlements' in ns['rollback']['preserve'],'ROLLBACK_STOP_WITHOUT_ERASING_EVIDENCE')
    realtime=d['realtime_shadow'];cohort=realtime['cohort'];member=realtime['membership']
    require(realtime['future_original_observation']==dict(evidence_origin='PIT_OBSERVED',execution_mode='SHADOW',namespace='SHADOW_V4',requires='EXACT_ACCEPTED_CLOCK_SLOT_SOURCE_VISIBILITY_AND_AUTHORIZED_FUTURE_RUNTIME'),'FUTURE_OBSERVED_RUNTIME_AUTHORITY_REQUIRED')
    require(realtime['evidence_origin_enum']==['PIT_OBSERVED','RECONSTRUCTED_ASOF','RECONSTRUCTED_CORRECTED','DIAGNOSTIC_NON_PIT'] and realtime['execution_mode_enum']==['PRODUCTION','SHADOW','REPLAY'],'EXACT_ORIGIN_MODE_ENUMS')
    require(realtime['reconstruction_upgrade'] is False and realtime['FEP_feedback'] is False,'NO_REPLAY_FEP_FEEDBACK')
    require(cohort['authority']==ref('config/v4_15_cohort_contract_v1.json',root) and cohort['enrollment_key']==['logical_event_id','cohort_namespace'],'ACCEPTED_V15_COHORT_IDENTITY')
    require(cohort['ignore_selection']==['Focus','homepage_display_cap','manual_pin','UI_filter','ranking_visibility'] and cohort['stock_warm']=='NOT_APPLICABLE_NO_ACCEPTED_OWNER','COHORT_INDEPENDENT_OF_DISPLAY')
    require(cohort['preserve']==['T0','enrollment_id','control_assignment_ids','benchmark_ids','FIRST_OBSERVED'] and 'FIRST_REALTIME_ASSERTED' in cohort['original_rule'],'CORRECTION_NEVER_REENROLLS')
    require(member['daily_snapshots']==['industry_membership_snapshot','concept_membership_snapshot','sector_type_snapshot'] and member['append_only'] is True and member['future_basis']=='PIT_OBSERVED' and 'NEVER_PIT_OBSERVED' in member['historical_backfill_basis'],'DAILY_PIT_MEMBERSHIP_FROM_ACTUAL_START_ONLY')
    require(realtime['optional_BaoStock']==dict(role='SUPPLEMENTAL_ONLY',failure_blocks_pure_core=False,enrichment_mutates_core=False,strict_binding_promoted=False),'OPTIONAL_BAOSTOCK_ISOLATION')
    h=read(HEAD,root);require(realtime['capability_blocks']=={k:h['entries'][k] for k in ['A04_H21_CONSUMER','A04_HISTORICAL_AMOUNT_A','A08_CURRENT_RUNTIME']},'EXACT_CAPABILITY_ONLY_BLOCKS')
    for edge in ['Focus -> enrollment','UI Top-K -> enrollment','Forward outcome -> T0 state','FEP prediction -> Core/Radar','Corrected outcome -> T0','future source -> same-day decision']:require(edge in realtime['forbidden_feedback_edges'],'MANDATORY_NON_EDGE_'+edge)
    worker=d['settlement_worker']
    require(worker['horizons']==[1,3,5,10,20] and worker['result_key']==['enrollment_id','horizon','outcome_contract_id','evaluation_source_digest'],'ACCEPTED_DUE_HORIZONS_AND_RESULT_IDENTITY')
    require(worker['queue_key']==['namespace','model_contract_id','state_lineage_id','enrollment_id','horizon','due_trade_date','outcome_contract_id'] and worker['delivery_key']==['queue_key','evaluation_source_digest'],'DURABLE_QUEUE_IDEMPOTENCY')
    require(worker['execution_order']==['ACCEPTED_SHADOW_PUBLICATION','DUE_PLANNER','DUE_QUEUE_OUTBOX','ACCEPTED_FUTURE_DATA_HEAD','SETTLEMENT','APPEND_EVALUATION_REVISION','READBACK'],'SOURCE_DUE_ORDER')
    require(worker['settle_invalidated_exited'] is worker['settle_UI_excluded'] is True and worker['raw_provider_fallback'] is worker['suspension_moves_horizon'] is worker['recompute_core_formulas'] is False,'NO_SELECTION_OR_FORMULA_REDESIGN')
    require(worker['future_read_guard']=='EXACT_ACCEPTED_SOURCE_AUTHORITY_AND_MARKET_SESSION_DUE_AND_AVAILABLE; NO_PRE_DUE_READ' and worker['unavailable_endpoint']=='PENDING_DUE_SOURCE_UNAVAILABLE_WITH_REASON; NOT_ZERO_OR_RIGHT_CENSOR','DUE_ENDPOINT_FAIL_CLOSED')
    require(worker['queue_semantics']==dict(delivery='AT_LEAST_ONCE',result='EXACT_SOURCE_IDEMPOTENT',claim='COMPARE_AND_SET_QUEUE_ITEM',ack='ONLY_AFTER_IMMUTABLE_RESULT_REVISION_ACCEPTED',failure='RETRY_WITH_BACKLOG_REASON_NO_SOURCE_FALLBACK',correction='NEW_EVALUATION_SOURCE_DIGEST_APPENDS_REVISION'),'OUTBOX_CORRECTION_IDEMPOTENCY')
    require(worker['preserve']==['T0','enrollment_id','control_assignment_ids','benchmark_ids','FIRST_OBSERVED','first_observed_result'] and worker['controls_benchmark_identity']=='FREEZE_T0; NO_REDRAW_NO_FUTURE_REFILL_NO_RENORMALIZATION','IMMUTABLE_SETTLEMENT_T0_AND_CONTROLS')
    require(worker['due_calendar']==read('data/v4/V4_15_ACCEPTED_HEAD.json',root)['bindings']['calendar'] and worker['formulas_authority']==read('data/v4/V4_15_ACCEPTED_HEAD.json',root)['bindings']['contract_package'],'NO_DUE_CALENDAR_OR_FORMULA_REPLACEMENT')
    require(worker['maturity_debt']['CURRENT_REAL_MATURITY_EVIDENCE']=='NONE' and worker['maturity_debt']['PROVED_HORIZONS']==[] and worker['maturity_debt']['UNPROVED_HORIZONS']==[1,3,5,10,20],'REAL_MATURITY_NONE')
    health=d['shadow_health'];stable=health['stability']
    require(health['capabilities']==CAPS and health['fields']==HEALTH_FIELDS,'CAPABILITY_SCOPED_HEALTH_RECEIPTS')
    require(stable['required_real_consecutive_sessions']==20 and stable['same_model_required'] is stable['rollback_drill_required'] is True and stable['replay_vector_backfill_counts'] is False,'STABLE_REAL_ONLY_COUNTERS')
    require(stable['temporal_leakage_max']==stable['duplicate_episode_corruption_max']==stable['core_identity_P0_violations_max']==0,'STABLE_ZERO_P0')
    require(stable['missed_or_unevaluable_session']=='BREAK_CONSECUTIVE_STREAK; NEVER_COUNT_OR_SKIP' and stable['P0_or_model_parameter_change']=='RESET_AFFECTED_WINDOW_AND_SHARED_DEPENDENCY_CONSUMERS','WINDOW_GAP_BOUNDARY_RESET')
    require(health['stock_provisional']['unique_signal_dates']==5 and health['stock_provisional']['unique_stock_positive_events']==30 and health['stock_provisional']['horizon']==5 and health['stock_provisional']['quality']=='OBSERVED_ONLY','ACCEPTED_STOCK_PROVISIONAL_COUNTERS')
    require(health['sector_rotation_provisional']['minimum_numeric_values'] is None and health['real_accumulation_blocks_unrelated_engineering'] is False,'NO_INVENTED_SECTOR_MINIMUM_OR_GLOBAL_DEBT_BLOCK')
    require(health['stock_provisional']['revision_counts_twice'] is health['stock_provisional']['INVALIDATION_counts_positive'] is health['stock_provisional']['settlement_P0_allowed'] is False and health['sector_rotation_provisional']['failed_counts_as_positive'] is health['sector_rotation_provisional']['pulse_substitutes_accepted'] is False,'NO_PROVISIONAL_COUNTER_INFLATION')
    return verify_vectors(d['machine_vectors'])

def validate(root=ROOT):
    root=Path(root).resolve();phase0=formalization(root)
    require(ref(R21_AUDIT,root)['sha256']=='d4545e994bdabfb25c27d25118008c14b544306344778fb0712e3b1be273789f','EXACT_R21_EXTERNAL_AUDIT')
    p=read('config/v4_16_contract_package_v1.json',root)
    names={'v4_16_'+n+('_v1' if n=='machine_vectors' else '_contract_v1') for n in NAMES}
    require(set(p['contracts'])==names,'ALL_SIX_CONTRACTS_EXIST')
    d={}
    for n in NAMES:
        key='v4_16_'+n+('_v1' if n=='machine_vectors' else '_contract_v1');b=p['contracts'][key]
        require(b['path']=='config/'+key+'.json','EXPLICIT_CONTRACT_PATH');d[n]=json.loads(exact(b,root))
    count=verify_semantics(d,root)
    require(p['execution_baseline']==BASE and p['current_audit_config']==ref(CONFIG,root) and p['current_audit_head']==ref(HEAD,root),'FORMALIZED_AUDIT_ENTRY_BINDING')
    require(read(p['phase0_gate']['path'],root)['PRE16_EXTERNAL_ACCEPTANCE_FORMALIZATION']=='PASS_LOCAL','PHASE0_BEFORE_PHASE1');exact(p['phase0_gate'],root)
    require(all(p[k] is False for k in ['production','shadow','focus','V4_16','runtime_implemented','runtime_authorized']) and p['REAL_SHADOW_OBSERVATIONS']==0,'PACKAGE_NOT_RUNTIME_PERMISSION')
    require(p['status']=='PASS_READY_FOR_EXTERNAL_AUDIT' and p['slot_capability']=='BLOCKED_AFFECTED_SCOPE_PENDING_ACCEPTED_CLOCK','COMPLETENESS_WITH_EXPLICIT_BLOCKED_CLOCK')
    registry=json.loads(exact(p['field_registry'],root));require(set(SLOT_FIELDS+HEALTH_FIELDS)<=set(registry['fields']),'MANDATORY_FIELD_REGISTRY')
    require(p['storage_design']['apply_permission'] is False and p['storage_design']['append_only'] is True,'STORAGE_DESIGN_NO_APPLY')
    require(p['non_edges']==['PRODUCTION_LEGACY_PRIOR -> SHADOW_V4_PRIOR','Focus -> enrollment','UI Top-K -> enrollment','Forward outcome -> T0 state','FEP prediction -> Core/Radar','Corrected outcome -> T0','future source -> same-day decision'],'PACKAGE_NO_FEEDBACK_EDGES')
    require(p['source_capability_matrix']==dict(clock='BLOCKED_AFFECTED_SCOPE',stock_warm='NOT_APPLICABLE_NO_ACCEPTED_OWNER',Amount_A_H21='BLOCKED_FORMAL_CONSUMER',historical_Amount_A='UNAVAILABLE_FORMAL_CONSUMER',A08_current_PREWATCH='OPEN_EXTERNAL_REAUDIT_NOT_ACTIVE_IN_SHADOW',BaoStock='OPTIONAL_SUPPLEMENTAL_ONLY',membership='FUTURE_OBSERVED_CAPTURE_ONLY; HISTORICAL_NOT_PIT',real_maturity='NOT_GRANTED',marked_benchmark='BLOCKED_UNSET_ACCEPTED_NUMERIC_GATES'),'PACKAGE_SOURCE_CAPABILITY_LIMITS')
    return dict(R22_V4_16_CONTRACT_FREEZE_ENTRY='PASS_LOCAL',V4_16_CONTRACT_COMPLETENESS='PASS_READY_FOR_EXTERNAL_AUDIT',V4_16_OBSERVATION_SLOT_CONTRACT='BLOCKED_AFFECTED_SCOPE',PRE16_GOVERNANCE=phase0['PRE16_GOVERNANCE'],GLOBAL_V4_16_CONTRACT_ENTRY_BLOCKERS=[],V4_16_RUNTIME='NOT_AUTHORIZED',REAL_SHADOW_OBSERVATIONS=0,SHADOW_STABLE='NOT_GRANTED',PROVISIONAL_FORWARD_EVIDENCE='NOT_GRANTED',FORWARD_SUPPORTED='NOT_GRANTED',V4_STAGE_ACCEPTED_HEAD='V4_00_TO_V4_15_ACCEPTED',V4_DATA_ACCEPTED_HEAD='2026-09-30',Production=False,Shadow=False,Focus=False,V4_16=False,machine_vectors=count,NEXT='STOP_WAIT_R22_INDEPENDENT_EXTERNAL_AUDIT')
if __name__=='__main__':print(json.dumps(validate()))
