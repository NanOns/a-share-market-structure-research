"""Independent literal oracles; owner helpers are implementation dependencies, not expected generators."""
from types import SimpleNamespace
from copy import deepcopy
from pathlib import Path
import pytest
from workbench_analysis.v4_13_io import FrozenContracts,digest
from workbench_analysis.v4_13_input_binder import AcceptedInputBinder
from workbench_analysis.v4_13_loo_runtime import LOOContextRuntime,select_sector,relative_sector
ROOT=Path(__file__).resolve().parents[1]
@pytest.fixture(scope='module')
def contracts():return FrozenContracts(ROOT)
def fixture_binder(c,count=6,missing=()):
    ids=['target','a','b','c','d','e'][:count];values=[99,-2,-1,1,2,3][:count]
    members=[dict(sector_id='I',sector_type='INDUSTRY',security_id=s,snapshot_id='synthetic',target_trade_date='2026-09-30') for s in ids]
    facts={s:dict(trade_date='2026-09-30',fields={k:dict(value=v,quality='ACCEPTED') for k in ['ret1','ret5','ret20','ret60','amount','rps20','close_minus_ma20','amount_ratio20','pos60','mdd20','close']}) for s,v in zip(ids,values) if s not in missing}
    b=SimpleNamespace(date='2026-09-30',cutoff='2026-10-02T15:00:00+08:00',memberships=members,current=facts,seed={s:s=='target' for s in ids},stock={'target':dict(rps5=70,rps20=85,rps20_delta3=1,stock_ret1=99,stock_ret5=99,compression_state='NORMAL',ma_structure_state='MIXED')},groups={'I':members},by_security={s:[r for r in members if r['security_id']==s] for s in ids},membership_complete=True,snapshot={'snapshot_id':'synthetic','source_revision_id':'s1'},membership_head={'facts':{'sha256':'independent-fixture','path':'synthetic'}},history={},history_digest=digest([]),refs=[],seed_capability=True,sessions=['2026-09-29','2026-09-30'])
    b.relationship=lambda s: AcceptedInputBinder.relationship(b,s)
    return b

def test_A01_dominant_excluded_independent_median_seed(contracts):
    r=LOOContextRuntime(contracts).compute(fixture_binder(contracts),'target','r1');n=r['contexts'][0]
    assert n['member_ids']==['a','b','c','d','e'];assert n['native_fields']['sector_rs1']['value']==1
    assert n['native_fields']['seed_width']['value']==0;assert n['native_fields']['seed_width']['n']==5
    assert r['algorithmic_support_sector']['quality']=='UNKNOWN'
def test_A02_minimum(contracts):
    r=LOOContextRuntime(contracts).compute(fixture_binder(contracts,2),'target','r1')
    assert r['relative_sector_state']['quality']=='UNKNOWN'
def test_A03_history_missing_relationship_independent(contracts):
    r=LOOContextRuntime(contracts).compute(fixture_binder(contracts),'target','r1')
    assert r['primary_industry']['value']=='I';assert r['primary_industry']['quality']=='KNOWN'
    assert r['supporting_concepts']['quality']=='NOT_APPLICABLE'
def test_A04_unknown_not_empty(contracts):
    b=fixture_binder(contracts);b.membership_complete=False
    assert b.relationship('target')['supporting_concepts']['value'] is None
    assert b.relationship('target')['primary_industry']['quality']=='UNKNOWN'
def test_A05_relation_conflict_and_concepts(contracts):
    b=fixture_binder(contracts);b.by_security['target']=[dict(sector_type='THEME',sector_id='Z'),dict(sector_type='THEME',sector_id='A'),dict(sector_type='INDUSTRY',sector_id='I')]
    assert b.relationship('target')['supporting_concepts']['value']==['A','Z']
    b.by_security['target'].append(dict(sector_type='INDUSTRY',sector_id='I2'))
    assert b.relationship('target')['primary_industry']['quality']=='UNKNOWN'
def test_A06_no_relation(contracts):
    b=fixture_binder(contracts);assert b.relationship('none')['primary_industry']['quality']=='NOT_APPLICABLE'
def test_A07_coverage_no_zero_imputation(contracts):
    r=LOOContextRuntime(contracts).compute(fixture_binder(contracts,missing=('a','b','c')),'target','r1')
    assert r['contexts'][0]['native_fields']['sector_quote_coverage']['value']==0.4
    assert r['relative_sector_state']['quality']=='UNKNOWN'
def test_A08_history_common_cohort_excludes_target(contracts):
    b=fixture_binder(contracts);prior=deepcopy(b.current)
    for r in prior.values():r['trade_date']='2026-09-29'
    m=deepcopy(b.memberships)
    for r in m:r['target_trade_date']='2026-09-29'
    b.history={1:dict(current=prior,memberships={'I':['target','a','b','c','d','e']},trade_date='2026-09-29',snapshot_id='synthetic',membership_rows=m,source_refs=[],accepted_owner_lineage=True)}
    r=LOOContextRuntime(contracts).compute(b,'target','r1')
    assert r['contexts'][0]['common_member_quality']['breadth_delta1']['common_count']==5
    assert r['contexts'][0]['native_fields']['breadth_delta1']['value']==0
def test_A09_relative_owner_literal_parity(contracts):
    r=LOOContextRuntime(contracts).compute(fixture_binder(contracts),'target','r1')
    assert r['relative_sector_state']['value']=='LEADING_ACCELERATING'
    assert r['relative_sector_state']['relative_substitutions']['rel_market_1']==98
@pytest.mark.parametrize('cap',[0,1,100])
def test_A10_selector_display_cap_independent(cap):
    candidates=[dict(sector_id='Z',quality='READY',confirmed_raw=True,warm_raw=False,emergence='HIGH',adjusted_seed_width=0.5),dict(sector_id='A',quality='READY',confirmed_raw=True,warm_raw=False,emergence='HIGH',adjusted_seed_width=0.5)]
    assert select_sector(candidates)['value']=='A'
def test_A11_historical_membership_fail_closed(contracts):
    b=AcceptedInputBinder(contracts,'2026-09-29','2026-10-02T15:00:00+08:00')
    assert b.membership_complete is False;assert b.relationship('target')['primary_industry']['quality']=='UNKNOWN'
def test_A12_fallback_unknown_no_io(contracts):
    b=AcceptedInputBinder(contracts,'2026-09-30','2026-10-02T15:00:00+08:00');assert not b.current and not b.history
    assert all(v==0 for v in b.counters.values())

def test_full_cross_section_rank_rebuilt_after_exclusion(contracts):
    b=fixture_binder(contracts)
    j=[dict(sector_id='J',sector_type='INDUSTRY',security_id='j'+str(i),snapshot_id='synthetic',target_trade_date=b.date) for i in range(5)]
    b.memberships+=j;b.groups['J']=j
    for m in j:b.current[m['security_id']]=dict(trade_date=b.date,fields={f:dict(value=1.25,quality='ACCEPTED') for f in ['ret1','ret5','ret20','ret60']})
    result=LOOContextRuntime(contracts).compute(b,'target','r1')
    assert result['contexts'][0]['native_fields']['sector_rs5_pct']['value']==0
    assert result['full_rank_universe']==['I','J']

def test_relative_uses_exact_stock_owner_not_native_member_alias(contracts):
    b=fixture_binder(contracts);b.stock['target']['stock_ret1']=2;b.stock['target']['stock_ret5']=2
    result=LOOContextRuntime(contracts).compute(b,'target','r1')
    assert result['relative_sector_state']['relative_substitutions']['rel_market_1']==1
