import pytest
from factors.engine import calculate

def test_market_session_lag(context):
    r,_=calculate(context)
    assert r['RET5']==pytest.approx(context.close.iloc[-1]/context.close.iloc[-6]-1)
    assert r['RET60__valid_sample_count']==61

def test_strict_minimum(context):
    r,_=calculate(context.tail(5))
    assert r['RET5']!=r['RET5']
