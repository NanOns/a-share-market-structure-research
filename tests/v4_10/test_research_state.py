from copy import deepcopy
import json
from pathlib import Path
import pytest
from src.v4.research_state import reduce_state, digest
from scripts.freeze_v4_10_contract import fixture, prior, with_prior
from scripts.verify_v4_10_state_reducer import check_vectors

ROOT=Path(__file__).resolve().parents[2]
VECTORS=json.loads((ROOT/'config/v4_10_machine_vectors_v1.json').read_text(encoding='utf8'))['vectors']

@pytest.mark.parametrize('vector',VECTORS,ids=[v['id'] for v in VECTORS])
def test_independent_vector(vector):
    if vector['expected_error']:
        with pytest.raises(ValueError,match=vector['expected_error']):reduce_state(vector['input'])
    else:
        r=reduce_state(vector['input'])
        assert {k:r[k] for k in vector['expected']}==vector['expected']
        assert reduce_state(vector['input'])==r

def test_independent_postcheck_has_complete_axis_and_transition_coverage():
    post,coverage=check_vectors()
    assert post['status']=='PASS'
    assert set(coverage['axes']['maturity'])=={'NONE','SEED','PREWATCH','WARM','CONFIRMED'}
    assert set(coverage['axes']['tracking'])=={'ACTIVE','FOLLOWUP','CLOSED'}
    assert set(coverage['axes']['health'])=={'IMPROVING','STABLE','WEAKENING','DAMAGED','EXHAUSTED','UNKNOWN'}

def test_unknown_interrupts_actual_downgrade_sequence():
    first=reduce_state(with_prior(fixture(stage='NONE'),prior()))
    second=fixture(stage='NONE');second['session_index']=21;second['detectors']['SEED']['value']='UNKNOWN'
    stale=reduce_state(with_prior(second,first))
    third=fixture(stage='NONE');third['session_index']=22
    resumed=reduce_state(with_prior(third,stale))
    assert first['downgrade_count']==1 and stale['downgrade_count']==0 and resumed['downgrade_count']==1
    assert resumed['maturity']=='PREWATCH' and resumed['final_eligibility']=='FALSE'

def test_expiry_baseline_accumulates_and_unknown_keeps_market_age():
    state=reduce_state(fixture())
    for offset,metric in enumerate([.9,1.8,2.7,3.1],1):
        x=fixture();x['session_index']=20+offset;x['delta3']=metric
        state=reduce_state(with_prior(x,state))
    assert state['improvement_baseline']==3.1 and state['expiry_count']==1
    assert state['market_age']==4

def test_real_input_missing_confirmation_is_unknown():
    x=fixture();x['mode']='ACCEPTED_FACT_INTERFACE'
    x['detectors']['CONFIRMED'].update(status='NOT_IMPLEMENTED',value='UNKNOWN')
    for stage,contract,param in [('SEED','BASE_SEED_V1','V4_07_BASE_SEED_PARAMETER_SET_V1'),
            ('PREWATCH','STOCK_PREWATCH_V1','V4_09_STOCK_PREWATCH_PARAMETER_SET_V1')]:
        x['detectors'][stage].update(status='IMPLEMENTED',contract_id=contract,parameter_set_id=param)
    r=reduce_state(x)
    assert r['final_eligibility']=='UNKNOWN' and r['episode_id'] is None

def test_false_or_unknown_cannot_be_coerced_from_python_boolean():
    for value in [False,True,None,0]:
        x=fixture();x['detectors']['SEED']['value']=value
        with pytest.raises(ValueError,match='INVALID_TRI_STATE'):reduce_state(x)

def test_next_session_reentry_keeps_old_episode_work():
    x=with_prior(fixture(),prior('NONE',tracking='FOLLOWUP',exit_session_index=19))
    r=reduce_state(x)
    assert r['parent_episode_id']=='FIXTURE_EPISODE' and r['episode_id']!='FIXTURE_EPISODE'
    assert r['preserved_followup_episode_ids']==['FIXTURE_EPISODE']

def test_same_session_revision_does_not_increment_counters():
    x=with_prior(fixture(stage='NONE'),prior(downgrade_candidate='NONE',downgrade_count=1,session_index=20))
    assert reduce_state(x)['downgrade_count']==1
    x=with_prior(fixture(),prior(expiry_count=9,session_index=20))
    assert reduce_state(x)['expiry_count']==9
