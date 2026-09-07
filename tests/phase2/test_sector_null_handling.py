from sector.phase2 import aggregate,top3
import pandas as pd

def test_all_missing_is_null_not_zero():
    assert pd.isna(aggregate(pd.Series([None,None]),'median')[0])
    assert aggregate(pd.Series([None,None]),'median')[1]==0
    assert top3(pd.Series([1]*7+[None]))[1]==7
