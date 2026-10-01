import json,hashlib
import pytest
from workbench_analysis.status_st_authority_r1 import produce_trading_status,produce_st,load_accepted_dated_evidence

def member(bar=True):return dict(security_id='fixture-entity',source_security_key='fixture-symbol',trade_date='2026-09-28',source_bar_present=bar)
def fact(field,value,start='2026-09-01',end=None):return dict(security_id='fixture-entity',source_security_key='fixture-symbol',field=field,value=value,effective_from=start,effective_to=end,authority_binding={'path':'fixture-approved-notice','sha256':'a'*64})

@pytest.mark.parametrize('provider',[None,'0','1'])
def test_actual_bar_owns_status_even_conflict(provider):
    r=produce_trading_status(member(),(),provider)
    assert r['status']=='ACTUAL_TRADED' and r['status_source']=='LOCAL_TDX_ACTUAL_BAR'
    assert r['provider_conflict']==(provider=='0')

@pytest.mark.parametrize('provider',[None,'0','1'])
def test_missing_bar_provider_never_mints_suspension(provider):assert produce_trading_status(member(False),(),provider)['status']=='UNKNOWN'

@pytest.mark.parametrize('value,expected',[('SUSPENDED','SUSPENDED'),('SHOULD_TRADE','DATA_GAP')])
def test_accepted_dated_owner_and_resumption(value,expected):
    f=fact('trading_status',value)
    assert produce_trading_status(member(False),(f,),'1')['status']==expected
    assert produce_trading_status(member(),(f,),'0')['status']=='ACTUAL_TRADED'

def test_conflicting_dated_sources_fail_closed():assert produce_trading_status(member(False),(fact('trading_status','SUSPENDED'),fact('trading_status','SHOULD_TRADE')))['status']=='UNKNOWN'

@pytest.mark.parametrize('value,expected',[('NORMAL','0'),('ST','1'),('STAR_ST','1'),('RISK_WARNING','1')])
def test_dated_st_states_and_suspension(value,expected):
    r=produce_st(member(False),(fact('st_state',value),),'0')
    assert r['is_st']==expected and r['provider_conflict']==(expected!='0')

def test_expired_st_is_not_filled_from_current_name_or_provider():
    assert produce_st(member(),(fact('st_state','ST',end='2026-09-27'),),'1')['is_st'] is None
    assert produce_st(member(),(fact('st_state','NORMAL',start='2026-09-28'),),'1')['is_st']=='0'

def test_alias_requires_exact_dated_key():
    f=fact('st_state','ST');f['source_security_key']='old-fixture-symbol'
    assert produce_st(member(),(f,),'1')['is_st'] is None

@pytest.mark.parametrize('boundary',['NEW_LISTING','DELISTED','LONG_SUSPENSION'])
def test_boundary_absence_does_not_invent_state(boundary):
    m={**member(False),'diagnostic_boundary':boundary}
    assert produce_trading_status(m)['status']=='UNKNOWN' and produce_st(m,(),'0')['is_st'] is None

def test_real_loader_rejects_provider_or_unaccepted_authority(tmp_path):
    p=tmp_path/'fact.json'
    for owner,accepted in [('BAOSTOCK','EXTERNALLY_ACCEPTED'),('OFFICIAL_EXCHANGE_NOTICE',None)]:
        p.write_text(json.dumps(dict(owner_kind=owner,external_acceptance=accepted,source_role='FIELD_AUTHORITY',facts=[])))
        c={'accepted_dated_evidence':[{'path':'fact.json','sha256':hashlib.sha256(p.read_bytes()).hexdigest()}]}
        with pytest.raises(ValueError,match='NOT_ACCEPTED'):load_accepted_dated_evidence(tmp_path,c)
