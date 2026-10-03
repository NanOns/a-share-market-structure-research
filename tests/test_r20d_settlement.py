import copy
import pytest
from pathlib import Path
from workbench_analysis.v4_15_settlement import price_path,benchmark,freeze_basket,freeze_controls,due_plan,VectorPriceSource,AcceptedPriceSource,SettlementRuntime
from workbench_analysis.v4_current_stage_authority import CurrentStageAuthority
from workbench_analysis.v4_15_persistence import Store

ROOT=Path(__file__).resolve().parents[1]
def row(close=10,high=11,low=9,**kw):return dict(close=close,high=high,low=low,verified_identity=True,verified_adjustment=True,T0_basis_verified=True,evaluation_basis_date='2026-09-30',transform_coefficients={'alpha':1,'beta':0},**kw)
@pytest.mark.parametrize('closes,expected', [([10,10],(0,.1,-.1,0)),([12,15],(.5,.6,0,0)),([8,6],(-.4,0,-.5,-.4)),([12,9,11],(.1,.3,-.2,-.25))])
def test_independent_formula_examples(closes,expected):
    result=price_path(10,[row(c,c+1,c-1) for c in closes],'2026-09-30')
    for key,value in zip(('R_N','MFE_N','MAE_N','PATH_MDD_CLOSE_N'),expected):assert result[key]==pytest.approx(value)
@pytest.mark.parametrize('update,state',[({'verified_identity':False},'IDENTITY_UNKNOWN'),({'verified_adjustment':False},'ADJUSTMENT_UNKNOWN'),({'evaluation_basis_date':'2026-09-29'},'ADJUSTMENT_UNKNOWN'),({'status':'CONFIRMED_SUSPENSION'},'SUSPENDED_AT_HORIZON'),({'status':'DELISTED'},'DELISTED_BEFORE_HORIZON'),({'close':None},'MATURED_DATA_MISSING')])
def test_no_coercion(update,state):
    r=row();r.update(update);out=price_path(10,[r],'2026-09-30');assert out['outcome_status']==state;assert out['R_N'] is None
def test_terminal_evidence_and_gaps():
    r=row(status='DELISTED',terminal_verified=True,terminal_evidence={'sha256':'proof'},terminal_value=4)
    assert price_path(10,[r],'2026-09-30')['R_N']==pytest.approx(-.6)
    missing=row();missing.update(close=None,high=None,low=None)
    out=price_path(10,[missing,row(12)],'2026-09-30');assert out['R_N']==pytest.approx(.2);assert out['MFE_N'] is None
    out=price_path(10,[row(status='CONFIRMED_SUSPENSION'),row(12)],'2026-09-30');assert out['actual_count']==1;assert out['R_N']==pytest.approx(.2)
def test_affine_common_basis_and_exclude_t0_extrema():
    r=row(6,7,5);r['transform_coefficients']={'alpha':.5,'beta':1}
    out=price_path(10,[r],'2026-09-30');assert out['evaluation_comparison_reference']==6;assert out['R_N']==pytest.approx(-1/3);assert out['MFE_N']==0
    assert price_path(10,[row(10,11,9)],'2026-09-30')['MFE_N']==pytest.approx(.1)
def test_calendar():
    sessions=['2026-09-24','2026-09-28','2026-09-29','2026-09-30']
    plan=due_plan(sessions,sessions[0],sessions[1]);assert plan[0]['due_date']=='2026-09-28';assert plan[1]['outcome_status']=='PENDING'
def test_fixed_benchmark_no_reweight():
    b=freeze_basket([{'security_id':'A','close':10},{'security_id':'B','close':20}],'2026-09-28')
    out=benchmark(b,{'A':row(12)},.2);assert out['benchmark_endpoint_coverage']==.5;assert out['observed_contribution']==.6;assert out['relative_return'] is None;assert out['marked_permission'] is False
    out=benchmark(b,{'A':row(12),'B':row(22)},.2);assert out['relative_return']==pytest.approx(.05)
def pool():
    return [dict(security_id=s,close=10,hard_safety=True,research_eligible=True,prewatch_final_eligible=s=='S',delta3=d,prior20_mean_amount=100+i,vol20=.1+i,RPS20=50+i,primary_industry='I') for i,(s,d) in enumerate([('S',1),('A',2),('B',2),('C',0),('D',-1)])]
def test_controls():
    p=pool();out=freeze_controls(p,p[0],2);assert out['A']['status']=='NOT_AVAILABLE';assert out['B']['control_entity_ids']==['A','B'];assert out['C']['control_count']==3;assert out['C']['control_entity_ids'][0]=='A';assert out['C']['match_scope']=='MATCH_SCOPE_INDUSTRY'
    p[0]['primary_industry']=None;assert freeze_controls(p,p[0],1)['C']['match_scope']=='MATCH_SCOPE_MARKET'
def test_unknown_delta_does_not_invent_ranking():
    p=pool()
    for r in p:r['delta3']=None
    controls=freeze_controls(p,p[0],3);assert controls['B']['control_entity_ids']==[];assert 'UNKNOWN_DELTA3_EXCLUDED' in controls['B']['reason_codes']
def test_benchmark_mixed_basis_and_distinct_t0_transform():
    basket=freeze_basket([{'security_id':'A','close':10}],'2026-09-29');r=row(6)
    r['T0_transform_coefficients']={'alpha':.5,'beta':1}
    result=benchmark(basket,{'A':r},None,'2026-09-30');assert result['return']==0
    result=benchmark(basket,{'A':r},None,'2026-09-29');assert result['benchmark_unknown_weight']==1;assert result['return'] is None
def test_availability_no_future():
    source=VectorPriceSource({'S':{'2026-09-30':row(available_at='2026-10-01')}})
    assert 'close' not in source.read('S','2026-09-30','2026-09-30','2026-09-30')
def test_persisted_revision_readback(tmp_path):
    auth=CurrentStageAuthority(ROOT);store=Store(tmp_path,'reports/v4_15_runtime_r20/test');runtime=SettlementRuntime(auth,store)
    e=store.append('enrollments','e',dict(enrollment_id='e',T0='2026-09-29',entity_id='S',comparison_reference=10))
    snapshot=store.append('snapshots','s',dict(trade_date='2026-09-29',universe=pool()))
    frozen=runtime.freeze_t0(e,snapshot);source=VectorPriceSource({r['security_id']:{'2026-09-30':row(12)} for r in pool()})
    first=runtime.settle(frozen,source,'2026-09-30',horizons=(1,));assert runtime.settle(frozen,source,'2026-09-30',horizons=(1,))==first
    correction=VectorPriceSource({'S':{'2026-09-30':row(11)}});second=runtime.settle(frozen,correction,'2026-09-30',horizons=(1,));assert first!=second
    readback=runtime.readback(frozen,'2026-09-30');assert readback['FIRST_OBSERVED'][1]['R_N']==pytest.approx(.2);assert readback['LATEST_CORRECTED'][1]['R_N']==pytest.approx(.1)
    assert store.read(frozen)['comparison_reference']==10
    cross=runtime.crossed_control(frozen,'A','2026-09-30',{'sha256':'publication'});assert store.read(cross)['ITT_RETAINED']
    competing=runtime.competing_outcome(frozen,[{'trade_date':'2026-09-30','event':'CONFIRMED'},{'trade_date':'2026-09-30','event':'INVALIDATED'}],'2026-09-30');assert store.read(competing)['competing_event']=='INVALIDATED'
    assert runtime.settle(frozen,source,'2026-09-30',horizons=(1,))==first
def test_strict_accepted_projection():
    auth=CurrentStageAuthority(ROOT);source=AcceptedPriceSource(auth,auth.data['component_artifacts']['ADJUSTED_DAILY']);assert source.evidence_class=='REAL_ACCEPTED_SOURCE_CAPABILITY_SCOPED';assert len(source.rows)>5000
    with pytest.raises(ValueError):AcceptedPriceSource(auth,{'path':'fake','sha256':'fake'})
    sid=next(iter(source.rows));assert 'close' not in source.read(sid,'2026-09-30','2026-09-30','2026-09-30')
@pytest.mark.parametrize('n',[1,3,5,10,20])
def test_all_horizons_independent_arithmetic(n):
    rows=[row(10+i,11+i,9+i) for i in range(1,n+1)]
    out=price_path(10,rows,'2026-09-30');assert out['R_N']==pytest.approx(n/10);assert out['MFE_N']==pytest.approx((n+1)/10);assert out['MAE_N']==0;assert out['PATH_MDD_CLOSE_N']==0
def test_sector_runtime_and_rotation(tmp_path):
    auth=CurrentStageAuthority(ROOT);store=Store(tmp_path,'reports/v4_15_runtime_r20/sector');runtime=SettlementRuntime(auth,store)
    e=store.append('enrollments','s',dict(enrollment_id='s',T0='2026-09-29',entity_type='SECTOR',entity_id='I',comparison_reference=None))
    snapshot=store.append('snapshots','s',dict(trade_date='2026-09-29',universe=pool()));frozen=runtime.freeze_t0(e,snapshot)
    source=VectorPriceSource({r['security_id']:{'2026-09-30':row(12)} for r in pool()});out=runtime.settle(frozen,source,'2026-09-30',horizons=(1,))
    value=store.read(out[0]);assert value['R_N']==pytest.approx(.2);assert value['price_path'][0]['price_extrema']=='CLOSE_ONLY'
    rotation=runtime.freeze_rotation('2026-09-30',['A','B'],'2026-09-29',{'A':10,'B':12});assert store.read(rotation)['pulse_reference']=='2026-09-29'
    with pytest.raises(ValueError):runtime.freeze_rotation('2026-09-30',['A'],'2026-09-30',{'A':10})
def test_reconstruction_does_not_fake_available_t0(tmp_path):
    auth=CurrentStageAuthority(ROOT);store=Store(tmp_path,'reports/v4_15_runtime_r20/reconstructed');runtime=SettlementRuntime(auth,store)
    e=store.append('enrollments','r',dict(enrollment_id='r',T0='2026-09-30',entity_id='S',cohort_namespace='RECONSTRUCTED_ASOF',comparison_reference=10))
    s=store.append('snapshots','r',dict(trade_date='2026-09-30',source_asof='2026-09-30',available_at=None,evidence_class='RECONSTRUCTED_ASOF',universe=pool()))
    assert runtime.freeze_t0(e,s)
    realtime=store.append('enrollments','first',dict(enrollment_id='first',T0='2026-09-30',entity_id='S',cohort_namespace='FIRST_OBSERVED',comparison_reference=10))
    with pytest.raises(ValueError):runtime.freeze_t0(realtime,s)
@pytest.mark.parametrize('alpha,beta',[(0,0),(-1,0),(float('nan'),0),(1,float('inf'))])
def test_bad_affine(alpha,beta):
    r=row();r['transform_coefficients']={'alpha':alpha,'beta':beta};assert price_path(10,[r],'2026-09-30')['outcome_status']=='ADJUSTMENT_UNKNOWN'
