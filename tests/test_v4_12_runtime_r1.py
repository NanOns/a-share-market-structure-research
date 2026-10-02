"""Scoped runtime checks against externally frozen independent expectations."""
from copy import deepcopy
from decimal import Decimal
import json
from pathlib import Path
import tempfile
import pytest
from scripts.v4_11_promotion_contract_r1 import ROOT
from scripts.replay_v4_12_runtime_r1 import business_vectors,sequence_vectors,synthetic_anchor
from scripts.verify_v4_12_runtime_supplemental_parity_r1 import run as supplemental_parity
from workbench_analysis.v4_12_structure_io import FrozenContracts,CandidateStore,digest
from workbench_analysis.v4_12_ast_runtime import ASTEngine,known,missing
from workbench_analysis.v4_12_input_binder import InputBinder
from workbench_analysis.v4_12_structure_engine import StructureEngine,SessionLedger
from workbench_analysis.v4_12_anchor_runtime import coordinate_view,create_anchor,create_event

CONTRACTS=FrozenContracts(ROOT)
BUSINESS=business_vectors(CONTRACTS)

@pytest.mark.parametrize('row',BUSINESS['rows'],ids=lambda r:r['vector_id'])
def test_runtime_independent_business_parity(row):assert row['status']=='PASS'

@pytest.mark.parametrize('name',[r['field'] for r in CONTRACTS.config['field_registry']['fields'] if r['field_role']=='BLOCKED_CAPABILITY'])
def test_blocked_capability_cannot_receive_claimed_known(name):
    binder=InputBinder(CONTRACTS,'2026-09-30','2026-10-02T06:00:00+00:00')
    with pytest.raises(ValueError,match='UNKNOWN_ACCEPTED_CAPABILITY_UNAVAILABLE'):
        binder.check_input_claim(name,dict(quality='KNOWN',producer_contract_id=binder.fields[name]['producer_contract_id']))

@pytest.mark.parametrize('namespace',CONTRACTS.entry['forbidden_namespaces']+['D2[t]','same-day Event','future dates','raw OHLC fallback','V4-11 candidate'])
def test_runtime_forbidden_namespace(namespace):
    engine=StructureEngine(CONTRACTS,'2026-09-30','2026-10-02T06:00:00+00:00')
    with pytest.raises(ValueError,match='FORBIDDEN_RUNTIME_INPUT_NAMESPACE'):engine.evaluate('SYNTHETIC',extra_namespaces={namespace:{}})

@pytest.mark.parametrize('case',['cash_dividend','bonus_split','rights_issue','same_day_revision','cross_company_action_support'])
def test_cross_basis_is_unknown_original_immutable(case):
    anchor=synthetic_anchor(CONTRACTS);before=digest(anchor);view=coordinate_view(anchor,anchor['anchor_price_basis'],case,'2026-09-30','r2')
    assert view['quality']=='UNKNOWN' and view['reason']=='PRICE_BASIS_MISMATCH'
    assert view['lower'] is None and digest(anchor)==before

def test_same_basis_native_coordinate_conversion_is_not_identity_by_coefficients():
    anchor=synthetic_anchor(CONTRACTS);anchor['frozen_transform_coefficients'].update(mul='.5',add='1')
    view=coordinate_view(anchor,anchor['anchor_price_basis'],anchor['adjustment_source_revision'],'2026-09-30','r1')
    assert Decimal(view['lower'])==6
    wrong=coordinate_view(anchor,anchor['anchor_price_basis'],'different_revision','2026-09-30','r1')
    assert wrong['quality']=='UNKNOWN'

def test_sequences_and_quality_correction():
    result=sequence_vectors(CONTRACTS)
    assert result['status']=='PASS' and result['total']==33
    assert [r['actual_count'] for r in result['quality_correction']]==[1,0,1]

def test_missing_never_becomes_false_and_priority_stops():
    ast=ASTEngine(CONTRACTS.config,{'prior_recovery_failed':None})
    result=ast.target('recovery');assert result.value is None and result.reasons
    assert result.matched_rule_id=='machines/recovery/rules/0'

def test_kleene_decisive_false_is_not_unknown_coercion():
    ast=ASTEngine(CONTRACTS.config,{'C':None})
    node={'op':'and','args':[{'field':'C'},{'op':'eq','args':[{'math_constant':'ONE'},{'math_constant':'ZERO'}]}]}
    assert ast.evaluate(node,'probe').value is False
    assert ast.evaluate({'op':'not','args':[{'field':'C'}]},'probe').value is None

def test_nonpositive_denominator_unknown():
    ast=ASTEngine(CONTRACTS.config,{})
    result=ast.evaluate({'op':'div','args':[{'math_constant':'ONE'},{'math_constant':'ZERO'}]},'probe')
    assert result.value is None and result.reasons==('NONPOSITIVE_DENOMINATOR',)

def test_invalid_and_nonfinite_input_unknown():
    assert ASTEngine(CONTRACTS.config,{'C':'NaN'}).field('C').value is None
    assert ASTEngine(CONTRACTS.config,{'C':'wrong'}).field('C').value is None

def test_unknown_field_never_defaults_core():
    binder=InputBinder(CONTRACTS,'2026-09-30','2026-10-02T06:00:00+00:00')
    with pytest.raises(ValueError,match='FALSE_ACCEPTED_OWNER_CLAIM'):binder.check_input_claim('unknown_F0',dict(quality='KNOWN',producer_contract_id='CORE_FACTOR_V1'))

def test_no_local_external_field_claim():
    binder=InputBinder(CONTRACTS,'2026-09-30','2026-10-02T06:00:00+00:00')
    with pytest.raises(ValueError,match='LOCAL_FIELD_CANNOT_BE_F0'):binder.check_input_claim('distance_zone',dict(producer_contract_id=binder.fields['distance_zone']['producer_contract_id']))

def test_provider_or_candidate_digest_replacement_rejected():
    binder=InputBinder(CONTRACTS,'2026-09-30','2026-10-02T06:00:00+00:00')
    with pytest.raises(ValueError,match='SOURCE_DIGEST_NOT_ACCEPTED'):
        binder.check_input_claim('C',dict(quality='KNOWN',producer_contract_id=binder.fields['C']['producer_contract_id'],source_namespace='F0_ACCEPTED',time_role='T',source_digest='0'*64))

def test_future_source_and_future_date_rejected():
    binder=InputBinder(CONTRACTS,'2026-09-30','2026-09-30T16:00:00+00:00')
    with pytest.raises(ValueError,match='FUTURE_SOURCE'):binder.bind('SYNTHETIC')
    with pytest.raises(ValueError,match='FUTURE_DATE'):StructureEngine(CONTRACTS,'2026-10-03','2026-10-03T00:00:00+00:00')

def test_same_day_prior_snapshot_rejected():
    (ROOT/'tmp').mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='runtime_prior_probe_',dir=ROOT/'tmp') as directory:
        store=CandidateStore(ROOT,Path(directory).relative_to(ROOT).as_posix())
        payload=dict(trade_date='2026-09-30',security_id='SYNTHETIC',contract_digest=CONTRACTS.digest,namespace='Frozen D1[t-1]',available_at='2026-10-02T00:00:00+00:00')
        ref=store.json('same_day.json',payload)
        with pytest.raises(ValueError,match='SAME_DAY_OR_FOREIGN_PRIOR_D1'):
            InputBinder(CONTRACTS,'2026-09-30','2026-10-02T06:00:00+00:00').bind('SYNTHETIC',dict(artifact=ref))

def test_prior_candidate_requires_manifest_not_an_unsealed_helper():
    with tempfile.TemporaryDirectory(prefix='runtime_prior_probe_',dir=ROOT/'tmp') as directory:
        store=CandidateStore(ROOT,Path(directory).relative_to(ROOT).as_posix())
        payload=dict(trade_date='2026-09-29',security_id='SYNTHETIC',contract_digest=CONTRACTS.digest,namespace='Frozen D1[t-1]',available_at='2026-10-02T00:00:00+00:00')
        ref=store.json('unsealed.json',payload)
        with pytest.raises(ValueError,match='PRIOR_D1_CANDIDATE_MANIFEST_REQUIRED'):
            InputBinder(CONTRACTS,'2026-09-30','2026-10-02T06:00:00+00:00').bind('SYNTHETIC',dict(artifact=ref))

def test_append_only_store_idempotent_and_conflict_rejected():
    with tempfile.TemporaryDirectory(prefix='runtime_store_probe_',dir=ROOT/'tmp') as directory:
        store=CandidateStore(ROOT,Path(directory).relative_to(ROOT).as_posix());first=store.json('revision_r1.json',{'state':'UNKNOWN'})
        assert first==store.json('revision_r1.json',{'state':'UNKNOWN'})
        with pytest.raises(ValueError,match='IMMUTABLE_REVISION_CONFLICT'):store.json('revision_r1.json',{'state':'KNOWN'})
        store.json('revision_r2.json',{'state':'UNKNOWN'});assert (ROOT/first['path']).exists()

def test_anchor_event_episode_binding_immutable():
    anchor=synthetic_anchor(CONTRACTS);event=create_event(CONTRACTS,anchor,'r1');before=digest(event)
    other=synthetic_anchor(CONTRACTS,dict(price_basis='OTHER',adjustment_source_revision='r2'))
    assert other['anchor_id']!=anchor['anchor_id']
    assert event['anchor_id']==anchor['anchor_id'] and digest(event)==before
    assert event['frozen_invalidation_ast']==CONTRACTS.config['machine_ast']['definitions']['episode_invalidated']

def test_new_anchor_no_self_confirmation():
    ledger=SessionLedger(CONTRACTS,'2026-09-30',['2026-09-29','2026-09-30'],'SYNTHETIC')
    values={**CONTRACTS.config['machine_vectors']['defaults'],'C':11,'lo':10,'hi':10,'L':10,'H':12,'CLV':.7}
    result=ledger.observe('2026-09-30','r1',True,values)
    assert result['market_age']==result['evaluable_count']==result['held_count']==0
    assert result['support']=='IDLE' and result['acceptance']!='ACCEPTED'

def test_supplemental_authority_and_time_domain_parity():
    assert len(supplemental_parity())==2

def test_real_candidate_unknown_readback():
    from scripts.validate_v4_12_runtime_r1 import validate
    r=validate();assert r['status']=='PASS' and r['universe_count']==5224 and r['raw_fallback_count']==0
