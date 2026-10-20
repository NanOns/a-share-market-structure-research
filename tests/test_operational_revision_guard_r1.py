import json
from pathlib import Path
import pytest
from workbench_analysis.r43_owner_replay import ref
from workbench_analysis.operational_revision_guard_r1 import detect
from workbench_analysis.operational_increment_plan_v1 import verify_history_overlap

def fixture(tmp_path):
    kernel=tmp_path/'src/v4/factors/core.py';kernel.parent.mkdir(parents=True);kernel.write_text('original kernel')
    generation=tmp_path/'generation.json';generation.write_text(json.dumps(dict(gbbq='accepted-factor',member_sources={'member':'accepted-member'})))
    binding=ref(tmp_path,kernel)
    parent=dict(accepted_trade_date='2026-10-12',source_registry={'2026-10-12':dict(generation=ref(tmp_path,generation))},accepted_algorithm_bindings=[binding])
    head=tmp_path/'HEAD.json';head.write_text(json.dumps(parent))
    return parent,kernel,head

def test_normal_uses_accepted_generation_not_old_bootstrap(tmp_path):
    parent,_,head=fixture(tmp_path);before=head.read_bytes()
    result=detect(tmp_path,parent,'accepted-factor',{'member':'accepted-member'})
    assert result['status']=='APPEND_DAY' and result['numeric_bindings'][0]['unchanged']
    assert head.read_bytes()==before

@pytest.mark.parametrize('kind',['factor','membership','algorithm'])
def test_revision_blocks_append_and_leaves_head_unchanged(tmp_path,kind):
    parent,kernel,head=fixture(tmp_path);before=head.read_bytes()
    factor='accepted-factor';members={'member':'accepted-member'}
    if kind=='factor':factor='revised-factor'
    elif kind=='membership':members['member']='revised-member'
    else:kernel.write_text('changed numerical kernel')
    result=detect(tmp_path,parent,factor,members)
    assert result['status']=='RANGE_REPAIR_REQUIRED' and result['revisions']
    assert head.read_bytes()==before

@pytest.mark.parametrize('field',[1,5,6])
def test_old_raw_bar_amount_volume_revision_is_explicit_and_head_unchanged(tmp_path,field):
    _,_,head=fixture(tmp_path);before=head.read_bytes()
    raw=[20261012,1000,1100,900,1050,100.0,200]
    saved=[dict(security_id='sid',bars=[dict(trade_date='2026-10-12',raw_ohlc=[10,11,9,10.5],amount=100.0,volume=200)])]
    raw[field]+=1
    with pytest.raises(ValueError,match='RANGE_REPAIR_REQUIRED:SOURCE_HISTORY_REVISION'):
        verify_history_overlap({'sid':(None,[raw])},saved)
    assert head.read_bytes()==before

def test_history_unchanged_is_read_only(tmp_path):
    _,_,head=fixture(tmp_path);before=head.read_bytes()
    raw=[20261012,1000,1100,900,1050,100.0,200]
    saved=[dict(security_id='sid',bars=[dict(trade_date='2026-10-12',raw_ohlc=[10,11,9,10.5],amount=100.0,volume=200)])]
    verify_history_overlap({'sid':(None,[raw])},saved)
    assert head.read_bytes()==before


def test_actual_execution_archive_not_stale_workspace_module(tmp_path):
    parent,kernel,_=fixture(tmp_path)
    archived=tmp_path/'executed/core.py';archived.parent.mkdir();archived.write_bytes(kernel.read_bytes())
    execution=dict(ref(tmp_path,archived),module_path='src/v4/factors/core.py')
    kernel.write_text('stale unused workspace module')
    result=detect(tmp_path,parent,'accepted-factor',{'member':'accepted-member'},execution_bindings=[execution])
    assert result['status']=='APPEND_DAY'
    archived.write_text('archive tampered')
    with pytest.raises(ValueError,match='DIGEST_MISMATCH'):
        detect(tmp_path,parent,'accepted-factor',{'member':'accepted-member'},execution_bindings=[execution])


def test_successor_execution_set_may_fall_back_to_exact_predecessor_binding(tmp_path):
    parent,kernel,_=fixture(tmp_path)
    result=detect(tmp_path,parent,'accepted-factor',{'member':'accepted-member'},execution_bindings=[])
    binding=result['numeric_bindings'][0]
    assert result['status']=='APPEND_DAY'
    assert binding['execution_binding_source']=='PREDECESSOR_HEAD'
    assert binding['executed_binding']['path']=='src/v4/factors/core.py'
    assert binding['actual_sha256']==binding['accepted_sha256']
    kernel.write_text('changed numerical kernel')
    changed=detect(tmp_path,parent,'accepted-factor',{'member':'accepted-member'},execution_bindings=[])
    assert changed['status']=='RANGE_REPAIR_REQUIRED'
    assert changed['numeric_bindings'][0]['unchanged'] is False


def test_first_seen_unlinked_code_never_invents_ipo_price_limits():
    from workbench_analysis.r43_daily_price_limits import observed_listing_phase
    sessions=['2026-10-12','2026-10-13']
    assert observed_listing_phase(dict(first_seen_date='2026-10-13',list_date='2026-10-13',confirmed_ipo_date=None),'2026-10-13',sessions,'NORMAL')=='UNKNOWN'
    assert observed_listing_phase(dict(first_seen_date='2026-10-13',list_date='2026-10-13',confirmed_ipo_date='2026-10-13'),'2026-10-13',sessions,'NORMAL')=='IPO_FIRST_5_TRADING_DAYS'
    assert observed_listing_phase(dict(first_seen_date='2026-10-13',list_date='2026-10-13',confirmed_ipo_date='2020-01-01'),'2026-10-13',['2020-01-01','2020-01-02','2020-01-03','2020-01-06','2020-01-07','2026-10-12','2026-10-13'],'NORMAL')=='NORMAL'


def test_original_generation_policy_remains_baseline_without_market_admission(tmp_path):
    from workbench_analysis.operational_revision_guard_r1 import accepted_baseline
    parent,kernel,_=fixture(tmp_path);old=parent['accepted_algorithm_bindings']
    p=tmp_path/'old_policy.json';p.write_text(json.dumps(dict(accepted_algorithm_bindings=old)))
    generation=dict(adjustment_contract=dict(policy=ref(tmp_path,p)))
    parent['accepted_algorithm_bindings']=[dict(path='unaccepted_current_policy.py',sha256='a'*64)]
    bindings,policy,corrected=accepted_baseline(tmp_path,parent,generation)
    assert bindings==old and corrected is False and policy==ref(tmp_path,p)


def test_market_baseline_requires_both_strict_admissions_and_detects_next_revision(tmp_path,monkeypatch):
    import sys,types
    from workbench_analysis.operational_revision_guard_r1 import CORRECTED_MARKET_KEY
    from workbench_analysis import operational_runtime_acceptance_r1_1 as runtime
    parent,kernel,_=fixture(tmp_path)
    market=tmp_path/'src/workbench_analysis/r43_market_replay.py';market.parent.mkdir(parents=True);market.write_text('verified corrected market')
    current=parent['accepted_algorithm_bindings']+[ref(tmp_path,market)]
    policy=tmp_path/'accepted_runtime_policy.json';policy.write_text(json.dumps(dict(accepted_algorithm_bindings=current)))
    parent.update(accepted_algorithm_bindings=current,release_policy=ref(tmp_path,policy))
    parent[CORRECTED_MARKET_KEY]={};parent[runtime.KEY]={}
    checks=[]
    monkeypatch.setitem(sys.modules,'workbench_analysis.operational_market_context_correction_r1',types.SimpleNamespace(verify=lambda *a:checks.append('market')))
    monkeypatch.setattr(runtime,'verify',lambda *a:checks.append('runtime'))
    result=detect(tmp_path,parent,'accepted-factor',{'member':'accepted-member'})
    assert result['status']=='APPEND_DAY' and result['bounded_market_admission_verified'] is True and checks==['market','runtime']
    market.write_text('next unaccepted market revision')
    result=detect(tmp_path,parent,'accepted-factor',{'member':'accepted-member'})
    assert result['status']=='RANGE_REPAIR_REQUIRED'
    assert result['revisions']==['NUMERIC_ALGORITHM_REVISION:src/workbench_analysis/r43_market_replay.py']


def test_market_marker_alone_cannot_replace_generation_policy(tmp_path):
    from workbench_analysis.operational_revision_guard_r1 import CORRECTED_MARKET_KEY
    parent,_,_=fixture(tmp_path);parent[CORRECTED_MARKET_KEY]={}
    with pytest.raises(ValueError,match='MARKET_RUNTIME_ADMISSION_MISSING'):detect(tmp_path,parent,'accepted-factor',{'member':'accepted-member'})
