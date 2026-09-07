from sector.phase2 import aggregate
import pandas as pd

def test_zero_not_positive():
    assert aggregate(pd.Series([0,1,None,-1]),'positive')==(1/3,3)
