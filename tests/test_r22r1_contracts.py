"""Clock boundary, visibility and immutable machine-state fail-closed tests."""
import ast,inspect
from copy import deepcopy
import pytest
from scripts import validate_r22r1_contracts as o
from scripts.r22r1_io import *
from scripts.pre16_normalized_current_audit_reader import NormalizedCurrentAuditStatus
V=read(VECTORS)
@pytest.mark.parametrize('case',V['cases'],ids=lambda v:v['id'])
def test_independent_authored_clock_vectors(case):assert o.engineering_clock_case(case)==case['expected']
def test_full_independent_gate():assert o.validate()['status']=='PASS_LOCAL_READY_FOR_EXTERNAL_AUDIT'
def test_clock10_new_policy_and_window_reset():
    c=read(CLOCK);new=dict(c,contract_id='V4_16_CLOCK_CONTRACT_V2',version='2.0.0',scheduled_source_cutoff_local='21:01:00')
    assert o.revision_decision(c,new)==dict(new_policy_identity_required=True,reset_affected_window=True,rewrite_old_slots=False)
@pytest.mark.parametrize('field',['scheduled_source_cutoff_local','observation_publication_deadline_local','source_provider_available_at','system_available_at'])
def test_clock_change_cannot_reuse_policy(field):
    c=read(CLOCK);n=dict(c);n[field]='ALTERED'
    with pytest.raises(ValueError,match='NEW_CLOCK_VERSION'):o.revision_decision(c,n)
def test_no_changed_policy_no_reset():assert not o.revision_decision(read(CLOCK),read(CLOCK))['reset_affected_window']
@pytest.mark.parametrize('field',['receipt','accepted','integrity_pass'])
def test_mandatory_receipt_fail_closed(field):
    v=deepcopy(V['cases'][0]);v['mandatory_sources'][0][field]=False
    assert o.engineering_clock_case(v)=='REJECT_NO_PIT'
def test_one_late_mandatory_member_blocks_whole_set():
    v=deepcopy(V['cases'][0]);s=deepcopy(v['mandatory_sources'][0]);s['system_at']='2026-09-30T13:00:01Z';v['mandatory_sources'].append(s)
    assert o.engineering_clock_case(v)=='MISSED_RECONSTRUCTED_ONLY'
def test_non_utc_timestamp_rejected():
    v=deepcopy(V['cases'][0]);v['mandatory_sources'][0]['provider_at']='2026-09-30T20:59:00+08:00'
    assert o.engineering_clock_case(v)=='REJECT_NO_PIT'
def test_empty_mandatory_set_rejected():
    v=deepcopy(V['cases'][0]);v['mandatory_sources']=[]
    assert o.engineering_clock_case(v)=='REJECT_NO_PIT'
def test_v3_reader_canonical_alias_and_permissions():
    r=NormalizedCurrentAuditStatus();assert r.blockers('blocks_v4_16_contract_entry')==r.blockers('blocks_v4_16_runtime_activation')==[]
    assert r.blockers('blocks_affected_capability_in_shadow')==['A04_H21_CONSUMER','A04_HISTORICAL_AMOUNT_A','A08_CURRENT_RUNTIME']
    assert r.canonical_entry('AUD_A04_AMOUNT_A_FORWARD_CONSUMER')==r.canonical_entry('A04_H21_CONSUMER')
    assert not r.stage_permission()
@pytest.mark.parametrize('key',['A04_H21_CONSUMER','A04_HISTORICAL_AMOUNT_A','A08_CURRENT_RUNTIME','REAL_MATURED_ACCEPTED_SOURCE_SETTLEMENT_RUNTIME','HISTORICAL_PIT_EFFECTIVENESS'])
def test_normalization_cannot_change_capability(monkeypatch,key):
    real=o.read
    def mutated(path,root=ROOT):
        value=deepcopy(real(path,root))
        if path==HEAD:value['entries'][key]['current_state']='PASS'
        return value
    monkeypatch.setattr(o,'read',mutated)
    with pytest.raises(ValueError,match='V3_MACHINE'):o.normalize_compare(ROOT)
@pytest.mark.parametrize('field',['blocks_v4_16_contract_entry','blocks_v4_16_runtime_activation','blocks_affected_capability_in_shadow','blocks_production_cutover_for_scope'])
def test_normalization_cannot_change_boolean(monkeypatch,field):
    real=o.read
    def mutated(path,root=ROOT):
        value=deepcopy(real(path,root))
        if path==HEAD:value['entries']['GOV_PRE16_01'][field]=True
        return value
    monkeypatch.setattr(o,'read',mutated)
    with pytest.raises(ValueError,match='V3_MACHINE'):o.normalize_compare(ROOT)
@pytest.mark.parametrize('field,value',[('timezone','UTC'),('scheduled_source_cutoff_local','21:01:00'),('observation_publication_deadline_local','23:00:00'),('historical_v4_00c_claim',True),('publication_before_cutoff_allowed',False),('backdating_allowed',True),('market_session_only',False),('source_provider_available_at','OBJECTIVE_PROVIDER_TIME'),('shadow',True),('runtime_authorized',True)])
def test_clock_policy_mutation_rejected(monkeypatch,field,value):
    real=o.read
    def mutated(path,root=ROOT):
        c=deepcopy(real(path,root))
        if path==CLOCK:c[field]=value
        return c
    monkeypatch.setattr(o,'read',mutated)
    with pytest.raises(ValueError):o.validate(protected=False)
def test_oracle_never_imports_writer():
    tree=ast.parse(inspect.getsource(o))
    assert 'build_r22r1_contracts' not in inspect.getsource(o)
    assert all(not isinstance(n,ast.ImportFrom) or 'build' not in (n.module or '') for n in ast.walk(tree))
def test_historical_slot_clock_remains_unset():
    old=read('config/v4_16_observation_slot_contract_v1.json')
    assert old['clock_authority']['status']=='BLOCKED_AFFECTED_SCOPE'
    assert read(SLOT)['clock_authority']['contract']==ref(CLOCK)
