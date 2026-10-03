"""Adversarial capability boundaries; never manufacture historical accepted owners."""
import copy,json
from pathlib import Path
import pytest
from scripts.validate_r20r1_feasibility import inspect,exact,descriptor
from scripts.validate_r20r1_oracle import validate
from scripts.r20r1_scope import admit_matured_claim,assert_scope,DENIED
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads((ROOT/p).read_bytes())
def gate():return load('reports/r20r1/V4_15_CAPABILITY_SCOPE_GATE.json')
def test_independent_exact_feasibility():
    result=inspect()
    assert result['decision']=='NO_ACCEPTED_MATURED_LINEAGE_AVAILABLE'
    assert len(result['publication_inventory'])==24
    assert sum(p['accepted_source_publication'] for p in result['publication_inventory'])==1
    assert not any(p['admissible_for_real_maturity'] for p in result['publication_inventory'])
    assert result['current_real_T0']==result['data_cutoff']=='2026-09-30'
    assert result['future_read_count']==0
    assert [r['horizon'] for r in result['real_outcomes']]==[1,3,5,10,20]
def test_current_real_outcomes_are_pending():
    result=inspect();outcomes=[exact(r['binding']) for r in result['real_outcomes']]
    assert all(o['outcome_status']=='PENDING' for o in outcomes)
    with pytest.raises(ValueError):admit_matured_claim('PASS',{'outcomes':outcomes,'accepted_future_endpoint_read_count':0})
@pytest.mark.parametrize('outcomes,reads',[([{'outcome_status':'PENDING'}],1),([{'outcome_status':'OBSERVED'}],0),([],1),([{'outcome_status':'PENDING'}],0)])
def test_pending_or_zero_read_count_never_pass(outcomes,reads):
    with pytest.raises(ValueError,match='PENDING_OR_ZERO'):admit_matured_claim('PASS',{'outcomes':outcomes,'accepted_future_endpoint_read_count':reads})
@pytest.mark.parametrize('kind',['ENGINEERING_SYNTHETIC','MACHINE_VECTOR','HISTORICAL_PRICES_ONLY','RECONSTRUCTED_ASOF','RAW_PROVIDER_FALLBACK'])
def test_ineligible_evidence_never_grants_real_maturity(kind):
    with pytest.raises(ValueError):admit_matured_claim('PASS',{'evidence_class':kind,'cohort_namespace':'REALTIME_ACCEPTED','outcomes':[{'outcome_status':'OBSERVED'}],'accepted_future_endpoint_read_count':20})
@pytest.mark.parametrize('namespace',['RECONSTRUCTED_ASOF','SYNTHETIC','CORRECTED_RECONSTRUCTION','ENGINEERING_VECTOR'])
def test_reconstructed_and_synthetic_lineage_cannot_upgrade(namespace):
    with pytest.raises(ValueError):admit_matured_claim('PASS',{'evidence_class':'REAL_ACCEPTED_SOURCE_CAPABILITY_SCOPED','cohort_namespace':namespace,'outcomes':[{'outcome_status':'OBSERVED'}],'accepted_future_endpoint_read_count':20})
def valid_looking():return dict(evidence_class='REAL_ACCEPTED_SOURCE_CAPABILITY_SCOPED',cohort_namespace='REALTIME_ACCEPTED',outcomes=[{'outcome_status':'OBSERVED'}],accepted_future_endpoint_read_count=20,raw_provider_fallback=False,historical_prices_only=False,T0_freeze_before_future_read=True,independent_exact_maturity_proof=True)
@pytest.mark.parametrize('attack',['raw_provider_fallback','historical_prices_only','T0_freeze_before_future_read','independent_exact_maturity_proof','caller_asserted_pass_without_bound_evidence'])
def test_claimed_booleans_are_not_exact_maturity_proof(attack):
    evidence=valid_looking()
    if attack in ['raw_provider_fallback','historical_prices_only']:evidence[attack]=True
    elif attack!='caller_asserted_pass_without_bound_evidence':evidence[attack]=False
    with pytest.raises(ValueError):admit_matured_claim('PASS',evidence)
def test_real_denial_is_explicit_and_pit_denied():
    assert admit_matured_claim(DENIED,{})
    assert assert_scope(gate(),{})
    widened=gate();widened['HISTORICAL_PIT_EFFECTIVENESS']='PASS'
    with pytest.raises(ValueError):assert_scope(widened,{})
def test_independent_oracle():assert validate()['R20R1_INDEPENDENT_ORACLE']=='PASS_LOCAL'
@pytest.mark.parametrize('attack',['matured_pass','historical_pit_pass','generic_label','remove_binding','change_binding','production','shadow','focus','V4_16','accepted_head','stage_advance','data_advance','supersession_rewrite','new_T0_scope'])
def test_independent_scope_oracle_rejects_widening(attack):
    g=copy.deepcopy(gate())
    if attack=='matured_pass':g['REAL_MATURED_ACCEPTED_SOURCE_SETTLEMENT']='PASS'
    elif attack=='historical_pit_pass':g['HISTORICAL_PIT_EFFECTIVENESS']='PASS'
    elif attack=='generic_label':g['REAL_ACCEPTED_SOURCE_SETTLEMENT']='PASS_CAPABILITY_SCOPED'
    elif attack=='remove_binding':g['bindings'].pop('real_settlement')
    elif attack=='change_binding':g['bindings']['real_settlement']['sha256']='0'*64
    elif attack in ['production','shadow','focus']:g[attack.title()]=True
    elif attack=='V4_16':g[attack]=True
    elif attack=='accepted_head':g['V4_15_ACCEPTED_HEAD']='CREATED'
    elif attack=='stage_advance':g['V4_STAGE_ACCEPTED_HEAD']='V4_00_TO_V4_15_ACCEPTED'
    elif attack=='data_advance':g['V4_DATA_ACCEPTED_HEAD']='2026-10-01'
    elif attack=='supersession_rewrite':g['supersession']['historical_files_rewritten']=True
    else:g['REAL_ACCEPTED_SOURCE_T0_INTEGRATION']='FULL_PASS'
    with pytest.raises(ValueError):validate(gate=g)
@pytest.mark.parametrize('attack',['close_debt','invent_coverage','invent_reads','block_unrelated','permit_next_stage','unbound_evidence'])
def test_validation_debt_is_separate_and_fail_closed(attack):
    debt=load('reports/r20r1/OPEN_VALIDATION_DEBT.json')
    if attack=='close_debt':debt['status']='CLOSED'
    elif attack=='invent_coverage':debt['matured_real_horizons']=[20]
    elif attack=='invent_reads':debt['accepted_future_endpoint_read_count']=20
    elif attack=='block_unrelated':debt['policy']['blocks_unrelated_development']=True
    elif attack=='permit_next_stage':debt['policy']['does_not_authorize_next_stage']=False
    else:debt['evidence']=[]
    with pytest.raises(ValueError):validate(debt=debt)
def test_exact_bytes_and_path_escape_fail_closed():
    b=descriptor('data/v4/V4_14_ACCEPTED_HEAD.json');b['sha256']='0'*64
    with pytest.raises(ValueError):exact(b)
    with pytest.raises(ValueError):exact({'path':'../outside','bytes':0,'sha256':'0'*64})
def test_oracles_are_independent_of_writer_and_evaluators():
    for name in ['validate_r20r1_feasibility.py','validate_r20r1_oracle.py']:
        source=(ROOT/'scripts'/name).read_text()
        for prohibited in ['build_r20r1_scope','r20r1_scope import','v4_15_settlement','v4_15_radar_cohort']:
            assert prohibited not in source

def test_debt_increment_without_actual_maturity_stays_open_and_is_idempotent():
    from scripts.r20r1_maturity_debt import refresh
    first=refresh();assert refresh()==first
    state=exact(first)
    assert state['status']=='OPEN' and state['verified_maturity_receipts']==[]
    assert not state['blocks_unrelated_development'] and state['blocks_matured_real_claims']
    assert state['HISTORICAL_PIT_EFFECTIVENESS']=='NOT_GRANTED'
    assert not state['stage_promotion_authorized']

@pytest.mark.parametrize('attack',['synthetic_owner','unsealed_owner','reconstructed_lineage','fabricated_earlier_T0','wrong_head','wrong_data'])
def test_incremental_debt_requires_real_authority_before_accepting_prices(attack):
    from scripts.r20r1_maturity_debt import validate_packet
    p=load('reports/r20e/PRODUCER_RECEIPT.json');head=load('data/v4/V4_14_ACCEPTED_HEAD.json');seal=exact(head['bindings']['runtime_seal'])
    packet=dict(accepted_head=descriptor('data/v4/V4_14_ACCEPTED_HEAD.json'),data_head=descriptor('data/v4/V4_DATA_ACCEPTED_HEAD.json'),owner_publication=exact(p['real_publication'])['source_publication'],enrollment=p['real_enrollment'],freeze=p['real_freezes'][0],horizon=1)
    if attack=='synthetic_owner':packet['owner_publication']=seal['replay_publications'][0]
    elif attack=='unsealed_owner':packet['owner_publication']=descriptor('config/v4_15_machine_vectors_v1.json')
    elif attack=='wrong_head':packet['accepted_head']['sha256']='0'*64
    elif attack=='wrong_data':packet['data_head']['sha256']='0'*64
    elif attack=='fabricated_earlier_T0':packet['enrollment']=descriptor('config/v4_15_radar_cohort_machine_vectors_v1.json')
    with pytest.raises((ValueError,KeyError)):validate_packet(packet)
