"""Mechanical acceptance and independent frozen-contract scope negative vectors."""
import ast,inspect
from copy import deepcopy
import pytest
from scripts import validate_pre16_finalization as f
from scripts import validate_r22_contracts as o
from scripts.r22_io import ROOT,HEAD,ACCEPT,read,atomic
from scripts.pre16_final_current_audit_reader import FinalCurrentAuditStatus

@pytest.fixture
def contracts():
    return {n:deepcopy(read('config/v4_16_'+n+('_v1' if n=='machine_vectors' else '_contract_v1')+'.json')) for n in o.NAMES}

def test_phase0_independent_gate():assert f.validate()['PRE16_EXTERNAL_ACCEPTANCE_FORMALIZATION']=='PASS_LOCAL'

def test_only_external_governance_findings_close():
    h=read(HEAD);assert h['governance_findings']=={'GOV_PRE16_01':'EXTERNALLY_ACCEPTED_CLOSED','GOV_PRE16_02':'EXTERNALLY_ACCEPTED_CLOSED'}
    assert h['GLOBAL_V4_16_CONTRACT_ENTRY_BLOCKERS']==[]

@pytest.mark.parametrize('field,value',[('audited_remote_head','0'*40),('tested_source','0'*40),('tested_tag','refs/tags/WRONG'),('external_decision','PASS_FULL_RUNTIME'),('external_authority',{'path':f.AUDIT,'sha256':'0'*64,'bytes':8532}),('grant','V4_16_RUNTIME_GRANTED'),('production',True),('shadow',True),('focus',True),('V4_16',True)])
def test_formalization_fail_closed_external_authority(field,value):
    a=deepcopy(read(ACCEPT));a[field]=value
    with pytest.raises(ValueError):f.validate(accepted=a)

@pytest.mark.parametrize('key',['A04_H21_CONSUMER','A04_HISTORICAL_AMOUNT_A','A08_CURRENT_RUNTIME','REAL_MATURED_ACCEPTED_SOURCE_SETTLEMENT_RUNTIME','REALTIME_ACCEPTED_COHORT_MATURITY','HISTORICAL_PIT_EFFECTIVENESS'])
def test_formalization_never_closes_capability_debt(key):
    h=deepcopy(read(HEAD));h['entries'][key]['current_state']='EXTERNALLY_ACCEPTED_CLOSED'
    with pytest.raises(ValueError,match='MECHANICAL_ONLY'):f.validate(head=h)

def test_new_current_reader_uses_explicit_v2_and_returns_copies():
    r=FinalCurrentAuditStatus();assert r.global_contract_entry_blockers()==r.runtime_activation_blockers()==[]
    assert r.capability_shadow_blockers()==['A04_H21_CONSUMER','A04_HISTORICAL_AMOUNT_A','A08_CURRENT_RUNTIME']
    assert len(r.production_cutover_blockers())==34 and r.stage_permission() is False
    assert r.canonical_entry('AUD_A04_AMOUNT_A_FORWARD_CONSUMER')==r.canonical_entry('A04_H21_CONSUMER')
    e=r.canonical_entry('A04_H21_CONSUMER');e['affected_capabilities'].clear();assert r.canonical_entry('A04_H21_CONSUMER')['affected_capabilities']

def test_contract_completeness():assert o.validate()['V4_16_CONTRACT_COMPLETENESS']=='PASS_READY_FOR_EXTERNAL_AUDIT'

def test_missing_clock_is_explicit_affected_scope(contracts):
    s=contracts['observation_slot'];assert s['clock_authority']['status']=='BLOCKED_AFFECTED_SCOPE'
    assert s['clock_authority']['scheduled_cutoff_at'] is s['clock_authority']['observation_deadline'] is None
    assert read('reports/r22/R22_CLOCK_AUTHORITY_REPAIR_01.json')['engineering_block'] is False

@pytest.mark.parametrize('field',['scheduled_cutoff_at','observation_deadline','accepted_clock_binding'])
def test_cannot_invent_accepted_clock(contracts,field):
    contracts['observation_slot']['clock_authority'][field]='2026-10-01T08:00:00Z'
    with pytest.raises(ValueError,match='NO_INVENTED_ACCEPTED_CLOCK'):o.verify_semantics(contracts)

@pytest.mark.parametrize('name',o.NAMES)
def test_each_contract_denies_shadow_runtime(contracts,name):
    contracts[name]['shadow']=True
    with pytest.raises(ValueError,match='CONTRACT_NOT_RUNTIME_GRANT'):o.verify_semantics(contracts)

@pytest.mark.parametrize('field',['runtime_implemented','runtime_authorized','production','focus','V4_16'])
def test_contract_freeze_never_grants_runtime_or_cutover(contracts,field):
    contracts['realtime_shadow'][field]=True
    with pytest.raises(ValueError,match='CONTRACT_NOT_RUNTIME_GRANT'):o.verify_semantics(contracts)

@pytest.mark.parametrize('field',['SHADOW_STABLE','PROVISIONAL_FORWARD_EVIDENCE','FORWARD_SUPPORTED'])
def test_future_gate_not_claimed(contracts,field):
    contracts['shadow_health'][field]='PASS'
    with pytest.raises(ValueError,match='NO_EVIDENCE_GATE_OVERCLAIM'):o.verify_semantics(contracts)

@pytest.mark.parametrize('scenario',['ON_TIME_FIRST_SLOT','LATE_BACKFILL','SAME_DAY_R2','LEGACY_PRIOR','MISSING_PREVIOUS_SHADOW_SESSION','MODEL_PARAMETER_CHANGE','HISTORICAL_REPLAY','FOCUS_UI_EXCLUSION','PRE_DUE_ENDPOINT','DUE_SOURCE_UNAVAILABLE','SETTLEMENT_RERUN','CORRECTED_EVALUATION_SOURCE','CURRENT_MEMBERSHIP_BACKFILL','BAOSTOCK_UNAVAILABLE','CAPABILITY_ISOLATION','P0_STATE_VIOLATION','MISSED_MARKET_SESSION','LEGACY_PRODUCTION_ISOLATION','SOURCE_CORRECTION_AFTER_ENROLLMENT','DUPLICATE_LOGICAL_EPISODE','UNSET_CLOCK_AUTHORITY','GOVERNANCE_CAPABILITY_DEBT','ENGINEERING_MATURITY_VECTOR'])
def test_every_required_vector_has_independent_frozen_expected(contracts,scenario):
    v=contracts['machine_vectors'];assert o.verify_vectors(v)==23
    row=next(r for r in v['vectors'] if r['scenario']==scenario);row['expected']={'pretend_runtime_PASS':True}
    with pytest.raises(ValueError,match='FROZEN_VECTOR_EXPECTATION'):o.verify_vectors(v)

def test_missing_negative_family_rejected(contracts):
    contracts['machine_vectors']['vectors'].pop()
    with pytest.raises(ValueError,match='COMPLETE_VECTOR_FAMILIES'):o.verify_vectors(contracts['machine_vectors'])

@pytest.mark.parametrize('section,field,value',[('realtime_shadow','reconstruction_upgrade',True),('realtime_shadow','FEP_feedback',True),('shadow_namespace','legacy_prior_reads',True),('shadow_namespace','legacy_writes',True),('shadow_namespace','production_focus_changes',True),('shadow_namespace','default_UI_changes',True),('settlement_worker','settle_invalidated_exited',False),('settlement_worker','settle_UI_excluded',False),('settlement_worker','raw_provider_fallback',True),('settlement_worker','suspension_moves_horizon',True),('settlement_worker','horizons',[1,2,5]),('settlement_worker','result_key',['enrollment_id']),('realtime_shadow','revision_behavior','OVERWRITE_T0')])
def test_forbidden_feedback_namespace_due_and_correction(contracts,section,field,value):
    contracts[section][field]=value
    with pytest.raises(ValueError):o.verify_semantics(contracts)

def test_UI_never_filters_cohort(contracts):
    contracts['realtime_shadow']['cohort']['ignore_selection']=[]
    with pytest.raises(ValueError,match='COHORT_INDEPENDENT_OF_DISPLAY'):o.verify_semantics(contracts)

def test_BaoStock_failure_never_blocks_core(contracts):
    contracts['realtime_shadow']['optional_BaoStock']['failure_blocks_pure_core']=True
    with pytest.raises(ValueError,match='OPTIONAL_BAOSTOCK_ISOLATION'):o.verify_semantics(contracts)

def test_correction_cannot_redraw_controls(contracts):
    contracts['settlement_worker']['controls_benchmark_identity']='REDRAW_LATEST_CONTROLS'
    with pytest.raises(ValueError,match='IMMUTABLE_SETTLEMENT_T0_AND_CONTROLS'):o.verify_semantics(contracts)

def test_real_maturity_cannot_use_engineering_vectors(contracts):
    contracts['settlement_worker']['maturity_debt']['PROVED_HORIZONS']=[1]
    with pytest.raises(ValueError,match='REAL_MATURITY_NONE'):o.verify_semantics(contracts)

def test_replay_cannot_fill_twenty_sessions(contracts):
    contracts['shadow_health']['stability']['replay_vector_backfill_counts']=True
    with pytest.raises(ValueError,match='STABLE_REAL_ONLY_COUNTERS'):o.verify_semantics(contracts)

def test_sector_numeric_minimum_not_invented(contracts):
    contracts['shadow_health']['sector_rotation_provisional']['minimum_numeric_values']=30
    with pytest.raises(ValueError,match='NO_INVENTED_SECTOR_MINIMUM'):o.verify_semantics(contracts)

def test_independent_oracles_never_import_writer_or_business_runtime():
    for module in [o,f]:
        imports=[n.module for n in ast.walk(ast.parse(inspect.getsource(module))) if isinstance(n,ast.ImportFrom)]
        assert not any(n and any(word in n for word in ['build_','radar_cohort','settlement','v4_16_runtime']) for n in imports)

def test_explicit_paths_no_latest_discovery():
    source=inspect.getsource(o)+inspect.getsource(f)+inspect.getsource(FinalCurrentAuditStatus)
    assert all(word not in source for word in ['.glob(','.rglob(','mtime','latest_file'])

def test_atomic_namespace_refuses_business_write():
    with pytest.raises(ValueError,match='R22_CONTRACT_OUTPUT_ONLY'):atomic('data/v4/V4_STAGE_ACCEPTED_HEAD.json',{})

def test_current_stage_and_data_and_protected_bytes_unchanged():
    result=f.validate();assert len(result['protected_bindings'])==51
    assert read('data/v4/V4_STAGE_ACCEPTED_HEAD.json')['accepted_stage_range']=='V4_00_TO_V4_15_ACCEPTED'
    assert read('data/v4/V4_DATA_ACCEPTED_HEAD.json')['accepted_trade_date']=='2026-09-30'
    assert not (ROOT/'data/v4/V4_16_ACCEPTED_HEAD.json').exists()
