import pandas as pd
from factors.engine import calculate

def test_future_bar_not_used(context):
    first,_=calculate(context,cutoff=119)
    context.loc[120,['close','amount','high','low']]=999999
    second,_=calculate(context,cutoff=119)
    assert first.keys()==second.keys()
    for k in first:
        assert first[k]==second[k] or (pd.isna(first[k]) and pd.isna(second[k]))
