import pytest
from factors.engine import calculate

def test_extrema_and_distance(context):
    r,_=calculate(context)
    w=context.tail(20)
    assert r['POS20']==pytest.approx((w.close.iloc[-1]-w.low.min())/(w.high.max()-w.low.min()))
    assert r['DIST_HIGH20']==pytest.approx(w.close.iloc[-1]/w.high.max()-1)

def test_flat_range_null(context):
    context[['close','high','low']]=5
    r,_=calculate(context)
    assert r['POS20']!=r['POS20']
