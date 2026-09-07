from sector.phase2 import aggregate
import pandas as pd

def test_breadth_excludes_null():
    v,n=aggregate(pd.Series([1,-1,None]),'positive')
    assert v==.5 and n==2
