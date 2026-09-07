from sector.phase2 import top3
import pandas as pd
import pytest

def test_baseline_positive_return_top3():
    assert top3(pd.Series([1,2,3,4,0,-1,0,0]))[0]==pytest.approx(.9)

def test_small_or_zero_positive_is_null():
    assert pd.isna(top3(pd.Series([1]*7))[0])
    assert pd.isna(top3(pd.Series([-1]*8))[0])
