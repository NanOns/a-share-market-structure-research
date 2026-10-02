from copy import deepcopy
from pathlib import Path
import pytest
from src.v4.owner_inputs_r5 import project_seed,UNAVAILABLE

@pytest.fixture
def identity_records():
    sid='SEC-'+'A'*32
    context=dict(trade_date='2026-09-30',profile_row_publication_id='R5_TARGET_CANDIDATE',expected_board_counts={'MAIN':1},identity_ids=[sid])
    core=dict(security_id=sid,symbol='SH.600001',board='MAIN',trade_date=context['trade_date'],publication_id=context['profile_row_publication_id'],historical_as_recorded_claim=False,trading_status='ACTUAL_TRADED',states={},derived_fields={},primitive_quality={})
    return core,dict(fields={}),context

@pytest.mark.parametrize('status,expected',[('ACTUAL_TRADED',True),('SUSPENDED',False),('UNKNOWN',None),(None,None),('CONFLICT',None)])
def test_actual_status_authority_independent_of_raw_presence(identity_records,status,expected):
    core,factor,context=identity_records;core['trading_status']=status
    core['raw_bar_present']=status!='SUSPENDED'
    assert project_seed(core,factor,context)['actual_bar']['value'] is expected

@pytest.mark.parametrize('change',[{'security_id':'INVALID'},{'symbol':'OTHER'},{'board':'UNKNOWN_BOARD'},{'trade_date':'2026-09-29'},{'publication_id':'V4_05_OLD_ACCEPTED'},{'historical_as_recorded_claim':True}])
def test_identity_requires_full_candidate_binding(identity_records,change):
    core,factor,context=identity_records;core.update(change)
    assert project_seed(core,factor,context)['price_identity_READY']['value'] is None

def test_unknown_t_minus_1_even_when_reconstruction_computable(identity_records):
    core,factor,context=identity_records
    core.update(raw_previous_close=10,adjusted_previous_close=10,previous_ma20=9,close_t_minus_1=10,ma20_t_minus_1=9)
    fields=project_seed(core,factor,context)
    for f in ('close_t_minus_1','ma20_t_minus_1'):assert fields[f]==dict(value=None,reason=UNAVAILABLE)

def test_membership_is_not_unconditional_true(identity_records):
    core,factor,context=identity_records;context['identity_ids']=[]
    assert project_seed(core,factor,context)['research_universe']['value'] is None

def test_identity_not_bar_readiness(identity_records):
    core,factor,context=identity_records;core['trading_status']='SUSPENDED'
    facts=project_seed(core,factor,context)
    assert facts['actual_bar']['value'] is False and facts['price_identity_READY']['value'] is True
