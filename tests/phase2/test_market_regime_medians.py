from sector.phase2 import aggregate
import pandas as pd

def test_median_and_linear_quantile():
    assert aggregate(pd.Series([1,3,None]),'median')==(2,2)
    assert aggregate(pd.Series([1,3]),'p25')==(1.5,2)
