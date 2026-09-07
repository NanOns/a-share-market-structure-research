import numpy as np
import pytest
from factors.engine import calculate

def test_exponential_trend(context):
    context['close']=np.exp(np.arange(len(context))*.01)
    r,_=calculate(context)
    assert r['TREND_SLOPE_60']==pytest.approx(.01)
    assert r['TREND_R2_60']==pytest.approx(1)

def test_constant_r2_is_null(context):
    context['close']=5
    r,_=calculate(context)
    assert r['TREND_R2_20']!=r['TREND_R2_20']
