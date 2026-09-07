import pytest
from factors.engine import calculate

def test_path_dependent_drawdown(context):
    context.loc[101:,'close']=[10,20,10,15]+[15]*16
    r,_=calculate(context)
    assert r['MDD20']==pytest.approx(-.5)
