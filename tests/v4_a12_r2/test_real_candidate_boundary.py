"""Candidate boundaries and prospective compatibility; fixtures never register real owners."""
from pathlib import Path
from copy import deepcopy
import json,hashlib
import pytest
from workbench_analysis.status_st_authority_candidate_r2 import candidate_fact,bit
from workbench_analysis.source_authority_accepted_owners_v1 import require_accepted_owner,OwnerAcceptanceError,HEAD_PATH,REGISTRY_PATH,HEAD_CONTRACT,REGISTRY_CONTRACT,load_registered_owners

ROOT=Path(__file__).resolve().parents[2]
def owner(field):return json.loads((ROOT/f'reports/audits/A12_R2_OWNER_{field}_CANDIDATE_R1.json').read_text(encoding='utf8'))
def member(actual=False):return dict(security_id='TEST_ONLY_ID',source_security_key='TEST_ONLY_KEY',trade_date='2024-07-03',source_bar_present=actual)
@pytest.mark.parametrize('value',[None,'','UNKNOWN','2',True,False,0.5])
def test_unknown_never_means_suspended_or_normal(value):
    u=member();s=candidate_fact(u,{**u,'provider_tradestatus':value},owner('TRADING_STATUS'),field='TRADING_STATUS');i=candidate_fact(u,{**u,'is_st':value},owner('ISST'),field='ISST')
    assert s['status']=='UNKNOWN' and i['is_st'] is None
def test_actual_survives_provider_zero_with_explicit_conflict():
    u=member(True);s=candidate_fact(u,{**u,'provider_tradestatus':'0'},owner('TRADING_STATUS'),field='TRADING_STATUS')
    assert s['status']=='ACTUAL_TRADED' and s['provider_conflict']
def test_missing_should_trade_is_gap_not_suspension():
    u=member();assert candidate_fact(u,{**u,'provider_tradestatus':'1'},owner('TRADING_STATUS'),field='TRADING_STATUS')['status']=='DATA_GAP'
@pytest.mark.parametrize('mutation',['formal','scope','alias'])
def test_candidate_cannot_cross_formal_or_dated_boundary(mutation):
    u=member();p={**u,'is_st':'1'};kw={}
    if mutation=='formal':kw['formal_use']=True
    elif mutation=='scope':u['trade_date']=p['trade_date']='2026-09-28'
    else:p['source_security_key']='PREDECESSOR_PLACEHOLDER'
    with pytest.raises(ValueError):candidate_fact(u,p,owner('ISST'),field='ISST',**kw)
@pytest.mark.parametrize('field',['TRADING_STATUS','ISST'])
def test_real_pending_owner_rejected_by_a10(field):
    o=owner(field)
    assert load_registered_owners(ROOT)['owners']==[]
    with pytest.raises(OwnerAcceptanceError,match='PENDING_OWNER'):
        require_accepted_owner(ROOT,o['role_binding'],consumer_contract_id='DM01_FINAL_ALL_NINE',target_trade_date='2024-07-03',historical_mode=o['historical_mode'])
def write(root,path,obj):
    p=root/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(obj,sort_keys=True),encoding='utf8')
    return dict(path=path,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
@pytest.mark.parametrize('field',['TRADING_STATUS','ISST'])
def test_prospective_exact_acceptance_fixture_compatible(tmp_path,field):
    o=owner(field);old=o['supersedes'];oldpath=tmp_path/old['path'];oldpath.parent.mkdir(parents=True,exist_ok=True);oldpath.write_bytes((ROOT/old['path']).read_bytes())
    o.update(external_acceptance='EXTERNALLY_ACCEPTED',formal_consumer_authorization=True,accepted_at='2026-10-01T06:00:00Z',fixture_only=True)
    r=o['role_binding'];r.update(authority_status='EXTERNALLY_ACCEPTED',enabled_for_formal_consumer=True)
    b=write(tmp_path,'fixtures/owner.json',o)
    e=dict(owner_contract_id=o['contract_id'],field_id=field,artifact=b,source_role=r['role'],role_binding_id=r['role_binding_id'],**{k:o[k] for k in ['external_acceptance','formal_consumer_authorization','allowed_consumers','effective_scope','historical_mode','accepted_at','supersedes']})
    rb=write(tmp_path,REGISTRY_PATH,dict(contract_id=REGISTRY_CONTRACT,version=1,owners=[e],fixture_only=True));rb['version']=1
    write(tmp_path,HEAD_PATH,dict(contract_id=HEAD_CONTRACT,registry=rb,fixture_only=True))
    result=require_accepted_owner(tmp_path,r,consumer_contract_id='DM01_FINAL_ALL_NINE',target_trade_date='2024-07-03',historical_mode=o['historical_mode'],expected_owner_binding=b)
    assert result['status']=='PASS_EXACT_ACCEPTED_OWNER'
    assert load_registered_owners(ROOT)['owners']==[]
def test_source_matrix_is_real_and_retains_scope_limit():
    x=json.loads((ROOT/'reports/audits/A12_R2_REAL_SAMPLE_MATRIX_R1.json').read_text(encoding='utf8'))
    assert set(x['required_boards'])=={'SH_MAIN','SZ_MAIN','CHINEXT','STAR'}
    assert x['actual_local_provider_conflict_count']==4 and not x['synthetic_samples_used']
    assert x['positive_st_during_numeric_code_change'].startswith('NOT_OBSERVED')
def test_observed_daily_scope_does_not_authorize_uncaptured_date():
    o=json.loads((ROOT/'reports/audits/A12_R2_OBSERVED_DAILY_OWNER_ISST_CANDIDATE_R1.json').read_text(encoding='utf8'))
    u=member();u['trade_date']='2026-09-29'
    with pytest.raises(ValueError,match='FROZEN_DATED_RESPONSE_MISSING'):candidate_fact(u,{**u,'is_st':'0'},o,field='ISST')
