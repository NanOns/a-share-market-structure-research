"""Independent R8 authority vectors and malicious metadata rejection tests."""
from copy import deepcopy
import json
from pathlib import Path
import pytest
from scripts.v4_12_authority_oracle_r2 import vectors
from scripts.validate_v4_12_authority_r2 import authority_parity,coordinate_audit,unit_audit,validate
from scripts.validate_v4_12_contract_freeze_r1 import load_configs,FixtureExpressionVerifier,validate_envelope_fixture

CONFIG=load_configs()

def actual(vector):
    rows=CONFIG['field_registry']['fields'];r={x['field']:x for x in rows};subject=vector['subject']
    if subject=='delta3':return [r['delta3'][k] for k in ['accepted_source_field','producer_contract_id','accepted_head_path']]
    if subject=='near_high20_state':return [r[subject][k] for k in ['producer_contract_id','target_publication_available','field_role']]
    if subject=='unknown_f0':
        fake=deepcopy(r['C']);fake['field']='unregistered_F0';fake['logical_field']='unregistered_F0'
        try:authority_parity(rows+[fake])
        except AssertionError as error:return str(error).split(':')[0]
        return 'WRONGLY_ACCEPTED'
    if subject=='distance_zone':return [r[subject][k] for k in ['field_role','producer_contract_id']]
    if subject=='alpha_beta':
        assert r['alpha']['field_role']==r['beta']['field_role']
        return [r['alpha']['producer_contract_id'],r['alpha']['field_role'],CONFIG['anchor_coordinate_contract']['transform_capability']['alpha']]
    if subject=='prior_range20_atr':return [r[subject][k] for k in ['field_role','capability']]
    if subject=='pivot':
        assert r['pivot_low']['field_role']==r['pivot_low_strict']['field_role']
        return [r['pivot_low'][k] for k in ['field_role','producer_contract_id']]
    if subject=='slope_unit':
        param=next(p for p in CONFIG['parameter_set']['parameters'] if p['parameter_id']=='range_anchor_abs_slope20_max')
        return [r['slope20']['unit'],param['unit'],param['value']]
    if subject=='explicit_aliases':return {n:r[n]['accepted_source_field'] for n in ['ATR20','CLV','MA20','MA60']}
    if subject=='branch_local':
        values={**CONFIG['machine_vectors']['defaults'],'prior_recovery_exists':True,'post_creation_market_sessions':2,'post_creation_evaluable_sessions':2,
            'prior_recovery_held_count':1,'prior_adjacent_evaluable':True,'C':11,'recovery_line_view':10,
            'close_t_minus_1':None,'ma20_t_minus_1':None,'ret1':None}
        return FixtureExpressionVerifier(CONFIG,values).target('recovery')
    if subject=='missing_owner':
        row=r['near_high20_state']
        pack=dict(contract_id='V4_12_INPUT_V1',parameter_set_digest='0'*64,observation_trade_date='2026-09-30',cutoff='2026-10-02T15:00:00Z',security_id='SYNTHETIC',inputs={row['field']:dict(
            value='NEAR',quality='KNOWN',unknown_reason=None,producer_contract_id=row['producer_contract_id'],publication_id='SYNTHETIC',publication_digest='0'*64,
            trade_date='2026-09-30',available_at='2026-10-02T14:00:00Z',source_namespace=row['source_namespace'],time_role=row['time_role'],output_digest='0'*64,
            price_basis='QFQ',adjustment_source_revision='SYNTHETIC')})
        try:validate_envelope_fixture(CONFIG,pack)
        except ValueError as error:return str(error)
        return 'WRONGLY_ACCEPTED'
    if subject=='raw_bars':return [r['prior_range20_atr']['field_role'],r['prior_range20_atr']['raw_reconstruction_allowed']]
    raise AssertionError(subject)

@pytest.mark.parametrize('vector',vectors(),ids=lambda v:v['id'])
def test_independent_authority_vector(vector):assert actual(vector)==vector['expected']

@pytest.mark.parametrize('field,mutation',[
 ('delta3',{'producer_contract_id':'CORE_FACTOR_V1.RET'}),
 ('near_high20_state',{'producer_contract_id':'CORE_FACTOR_V1.PRICE_TECHNICAL'}),
 ('ATR20',{'accepted_source_field':'ATR20'}),
 ('slope20',{'unit':'ATR_per_actual_session'}),
 ('distance_zone',{'source_namespace':'F0_ACCEPTED'}),
 ('alpha',{'producer_contract_id':'CORE_FACTOR_V1.PRICE_TECHNICAL'}),
 ('pivot_low',{'field_role':'UPSTREAM_ACCEPTED'}),
 ('prior_range20_atr',{'raw_reconstruction_allowed':True}),
 ('ret1',{'target_publication_available':True}),
 ('C',{'accepted_head_sha256':'0'*64}),
 ('prior_delta3',{'time_role':'T'}),
 ('CLV',{'producer_contract_id':'CORE_FACTOR_V1'})])
def test_false_authority_claim_rejected(field,mutation):
    rows=deepcopy(CONFIG['field_registry']['fields']);next(r for r in rows if r['field']==field).update(mutation)
    with pytest.raises(AssertionError):authority_parity(rows)

def test_coordinate_cannot_be_core_authority():
    cfg=deepcopy(CONFIG);cfg['anchor_coordinate_contract']['accepted_authority']={'path':'data/v4/V4_03_ACCEPTED_HEAD.json'}
    with pytest.raises(AssertionError,match='COORDINATE_AUTHORITY'):coordinate_audit(cfg)

def test_slope_parameter_unit_parity():
    cfg=deepcopy(CONFIG);next(p for p in cfg['parameter_set']['parameters'] if p['parameter_id']=='range_anchor_abs_slope20_max')['unit']='ATR'
    with pytest.raises(AssertionError):unit_audit(cfg)

def test_prior_rps_publication_cannot_use_same_day():
    rows=deepcopy(CONFIG['field_registry']['fields']);row=next(r for r in rows if r['field']=='prior_delta3')
    row['target_publications']['2026-09-30']['trade_date']='2026-09-30'
    with pytest.raises(AssertionError,match='RPS_PRIOR_TIME'):authority_parity(rows)

def test_requiredness_is_consumer_local():
    rows={r['field']:r for r in CONFIG['field_registry']['fields']}
    assert rows['ret1']['required_by']==['recovery.BOUNCE_ONLY']
    assert rows['near_high20_state']['required_by']==['breakout.APPROACHING']
    assert not any(r['globally_required'] for r in rows.values())

def test_completeness_requires_authority_parity_not_file_presence():
    result=validate()
    assert result['authority_parity']['unresolved_false_accepted_claims']==0
    assert result['completeness']['authority_parity']=='PASS'
    assert result['completeness']['blocked_anchor_types']
    assert result['status'] in ['V4_12_R2_CONTRACT_AUTHORITY_REPAIR_CANDIDATE_READY_FOR_EXTERNAL_AUDIT','V4_12_R2_1_TIME_COUNTER_SEMANTICS_CANDIDATE_READY_FOR_EXTERNAL_AUDIT']

def test_r6r1_and_r1_ast_vectors_preserved():
    result=validate()
    assert all(p['byte_identical'] for p in result['protected_and_keep_proof'])
    assert result['independent_vector_oracle']['passed']==69
