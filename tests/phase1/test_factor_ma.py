import pytest
from factors.engine import calculate

def test_ma_includes_t(context):
    r,_=calculate(context)
    assert r['MA60']==pytest.approx(context.close.tail(60).mean())

def test_missing_not_skipped(context):
    context.loc[120,'close']=float('nan')
    r,_=calculate(context)
    assert r['MA5']!=r['MA5'] and r['MA5__valid_sample_count']==4
