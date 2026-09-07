import pytest
from factors.engine import calculate

def test_baseline_amount_ratio(context):
    r,_=calculate(context)
    assert r['AMOUNT_RATIO20']==pytest.approx(context.amount.iloc[-1]/context.amount.tail(20).mean())

def test_zero_amount(context):
    context['amount']=0
    r,_=calculate(context)
    assert r['AMOUNT_RATIO20']!=r['AMOUNT_RATIO20']
    assert r['AMOUNT_MA20']==0

def test_concentration_baseline_formula(context):
    r,_=calculate(context)
    returns=context.close.tail(21).pct_change().dropna().clip(lower=0)
    assert r['RETURN_CONCENTRATION_20']==pytest.approx(returns.max()/returns.sum())
