import numpy as np
import pytest
from factors.engine import calculate

def test_sample_standard_deviation(context):
    r,_=calculate(context)
    expected=np.std(np.log(context.close.tail(21).to_numpy()[1:]/context.close.tail(21).to_numpy()[:-1]),ddof=1)
    assert r['VOLATILITY20']==pytest.approx(expected)
