"""Literal rational action prices, full raw windows and adversarial input checks."""
from decimal import Decimal
from types import SimpleNamespace
import pytest
from workbench_analysis.exact_operational_core_candidate_r3 import transform_window,independent_affine

def action(day,cash=0,rights_price=0,bonus=0,rights=0,index=0,category=1):
    return SimpleNamespace(event_date=day,category=category,c1=cash,c2=rights_price,c3=bonus,c4=rights,
        source_record_index=index,security_id='SH.600000')

def bars():
    return [(20260928,1000,1200,900,1100,100.0,10,0),(20260929,1100,1300,1000,1200,200.0,20,0),
            (20260930,1200,1400,1100,1300,300.0,30,0)]

def test_same_day_actions_and_future_actions_use_literal_rational_price_chain():
    events=[action(20260929,cash=1,bonus=5,index=0),action(20260929,rights_price=4,rights=2,index=1),
            action(20261009,cash=999,index=2)]
    result=transform_window(bars(),events,{'1':{'formal_disposition':'PRICE_AFFECTING_SUPPORTED'}},'2026-09-30')
    # (10-.1)/1.5=6.6; (6.6*10+2*4)/12=37/6 -> 6.17.
    assert result[0]['qfq_ohlc'][0]==6.17
    assert result[0]['exact_coefficients']['qfq_mul']=='5/9'
    assert result[0]['exact_coefficients']['qfq_add']=='11/18'
    assert result[1]['qfq_ohlc']==[11.0,13.0,10.0,12.0]
    assert len(result)==len(bars())
    for row in result:
        expected=[independent_affine(Decimal(value)/100,int(row['trade_date'].replace('-','')),events,20260930)
            for value in row['raw_ohlc_cents']]
        assert expected==row['qfq_ohlc']

def test_unknown_action_is_preserved_only_as_crossing_bar_degradation():
    result=transform_window(bars(),[action(20260929,category=99)],{},'2026-09-30')
    assert len(result)==3 and result[0]['qfq_ohlc'] is None
    assert result[0]['blocked_events']==[{'date':20260929,'category':99}]
    assert result[1]['qfq_ohlc']==[11.0,13.0,10.0,12.0]

def test_half_cent_rounds_up_in_exact_rational_coordinate():
    raw=[(20260928,1955,2000,1900,1955,100.0,10,0)]
    events=[action(20260929,bonus=10)]
    result=transform_window(raw,events,{'1':{'formal_disposition':'PRICE_AFFECTING_SUPPORTED'}},'2026-09-30')
    assert result[0]['qfq_ohlc']==[9.78,10.0,9.5,9.78]
    assert independent_affine(Decimal('19.55'),20260928,events,20260930)==9.78

def test_exact_runtime_candidate_rejects_production_root_before_reading(monkeypatch):
    from workbench_analysis.operational_owner_adapter_v1 import replay
    monkeypatch.setenv('R4_NATIVE_ISOLATION','1')
    with pytest.raises(ValueError,match='ISOLATED_EXACT_CORE_CANDIDATE_REQUIRED'):
        replay('G:/codex work/大A交易','G:/codex work/大A交易/forbidden',[],{},
            membership_snapshot={},seed_registry={},observed_at='2026-10-09T12:00:00+08:00',exact_adjustment=True)

@pytest.mark.parametrize('case',['duplicate_day','float_price','reversed_high_low','zero_price','invalid_day','nonfinite_action','invalid_denominator'])
def test_exact_core_invalid_inputs_fail_without_a_fallback(case):
    raw=bars();events=[]
    if case=='duplicate_day':raw.append(raw[0])
    if case=='float_price':raw[0]=(raw[0][0],10.0,*raw[0][2:])
    if case=='reversed_high_low':raw[0]=(raw[0][0],1000,800,1200,*raw[0][4:])
    if case=='zero_price':raw[0]=(raw[0][0],0,*raw[0][2:])
    if case=='invalid_day':raw[0]=(20260230,*raw[0][1:])
    if case=='nonfinite_action':events=[action(20260929,cash=float('nan'))]
    if case=='invalid_denominator':events=[action(20260929,bonus=-10)]
    with pytest.raises((ValueError,ArithmeticError)):transform_window(raw,events,{},'2026-09-30')
