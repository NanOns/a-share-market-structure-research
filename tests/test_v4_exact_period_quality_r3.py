from workbench_analysis.exact_period_consumer_r3 import derive_exact_periods
from workbench_analysis.operational_daily_periods_v1 import derive_periods

MEMBER=dict(security_id='SEC-CANDIDATE',source_security_key='SH.600000')
SESSIONS=['2026-09-29','2026-09-30','2026-10-08','2026-10-09','2026-10-12','2026-10-13']
def bar(day,price,known=True):
    return dict(trade_date=day,raw_ohlc=[price,price+2,price-1,price+1],qfq_ohlc=[price,price+2,price-1,price+1] if known else None,amount=100,volume=10)
def month(out,cap='PERIOD_ADJUSTED'):
    return next(row for row in out[cap] if row['period_key']=='2026-10')

def test_missing_status_never_relabelled_as_adjustment_after_next_actual_bar():
    history=[bar('2026-09-30',10),bar('2026-10-09',20)]
    args=(MEMBER,history,{},SESSIONS,'2026-10-09','2026-10-31')
    old=month(derive_periods(*args));new=month(derive_exact_periods(*args))
    assert old['unknown_count']==1 and old['period_status']=='BLOCKED_BY_ADJUSTMENT'
    assert new['unknown_count']==1 and new['period_status']=='BLOCKED_BY_UNKNOWN_STATUS'
    assert new['original_kernel_period_status']==old['period_status']
    assert not new['PIT_ELIGIBLE'] and new['close'] is None

def test_true_adjustment_damage_stays_adjustment_even_with_unknown_status():
    history=[bar('2026-09-30',10),bar('2026-10-09',20,False)]
    row=month(derive_exact_periods(MEMBER,history,{},SESSIONS,'2026-10-09','2026-10-31'))
    assert row['unknown_count']==1 and row['period_status']=='BLOCKED_BY_ADJUSTMENT' and row['close'] is None

def test_known_suspension_is_not_unknown_and_is_never_inferred():
    history=[bar('2026-09-30',10),bar('2026-10-09',20)]
    row=month(derive_exact_periods(MEMBER,history,{'2026-10-08':'SUSPENDED'},SESSIONS,'2026-10-09','2026-10-31'))
    assert row['suspended_count']==1 and row['unknown_count']==0
    assert row['period_status']=='AS_OF_PARTIAL_READY'
    assert float(row['close'])==21 and row['volume']==10
