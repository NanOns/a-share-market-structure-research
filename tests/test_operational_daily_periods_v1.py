from workbench_analysis.operational_daily_periods_v1 import derive_periods

MEMBER = dict(security_id='S', source_security_key='SH.600000')
SESSIONS = ['2026-09-29', '2026-09-30', '2026-10-08', '2026-10-09', '2026-10-12', '2026-10-13']


def bar(day, value, q=None):
    return dict(trade_date=day, raw_ohlc=[value, value+2, value-1, value+1],
                qfq_ohlc=[value/2, (value+2)/2, (value-1)/2, (value+1)/2] if q is None else q,
                amount=100, volume=10)


def test_month_week_boundaries_and_partial_closed():
    out = derive_periods(MEMBER, [bar(d, v) for d,v in zip(SESSIONS[1:4], [10,20,30])], {}, SESSIONS,
                         '2026-10-09', '2026-10-31')
    raw = out['PERIOD_RAW']; adjusted = out['PERIOD_ADJUSTED']
    month = next(r for r in raw if r['period_key']=='2026-10')
    week = next(r for r in raw if r['period_key']=='2026-W41')
    assert month['period_view']=='AS_OF_PARTIAL' and month['amount']==200 and month['volume']==20
    assert [float(month[p]) for p in ('open','high','low','close')]==[20,32,19,31]
    assert week['period_view']=='CLOSED_ONLY'
    q = next(r for r in adjusted if r['period_key']=='2026-10')
    assert float(q['close'])==15.5 and q['price_basis']=='QFQ'
    assert q['amount']==month['amount']


def test_suspension_gap_and_adjustment_unknown_remain_explicit():
    history=[bar('2026-10-08', 20), bar('2026-10-12', 30, q=[])]
    out=derive_periods(MEMBER, history, {'2026-10-09':'SUSPENDED'}, SESSIONS, '2026-10-13', '2026-10-31')
    raw=next(r for r in out['PERIOD_RAW'] if r['period_key']=='2026-10')
    q=next(r for r in out['PERIOD_ADJUSTED'] if r['period_key']=='2026-10')
    assert raw['suspended_count']==1 and raw['unknown_count']==1
    assert raw['period_status']=='BLOCKED_BY_UNKNOWN_STATUS'
    assert q['close'] is None and q['period_status']=='BLOCKED_BY_ADJUSTMENT'


def test_revised_qfq_replays_history_deterministically():
    history=[bar('2026-10-08',20),bar('2026-10-09',30)]
    args=(MEMBER,history,{},SESSIONS,'2026-10-09','2026-10-31')
    assert derive_periods(*args)==derive_periods(*args)
    original=derive_periods(*args)
    history[0]['qfq_ohlc']=[1,2,0.5,1.5]
    revised=derive_periods(*args)
    assert original['PERIOD_RAW']==revised['PERIOD_RAW']
    assert original['PERIOD_ADJUSTED']!=revised['PERIOD_ADJUSTED']
