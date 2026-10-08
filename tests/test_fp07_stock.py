from workbench_service.stock_views import aggregate

def bar(day,close,quality='KNOWN'):
    return dict(trade_date=day,open=close,high=close+1,low=close-1,close=close,volume=10,amount=100,quality=quality)

def test_week_and_month_boundaries():
    rows=[bar('2026-09-25',10),bar('2026-09-28',12),bar('2026-09-30',14),bar('2026-10-01',15)]
    week=aggregate(rows,'W');month=aggregate(rows,'M')
    assert [r['actual_count'] for r in week]==[1,3]
    assert month[0]['open']==10 and month[0]['close']==14 and month[0]['volume']==30
    assert month[-1]['period_status']=='FORMING_AS_OF'

def test_unknown_adjustment_never_fills():
    rows=[bar('2026-09-28',12),bar('2026-09-30',14,'UNKNOWN')]
    result=aggregate(rows,'W')[0]
    assert result['quality']=='UNKNOWN' and result['close'] is None
    assert result['volume']==20
