import pandas as pd
from shadow_v2.diagnostics import up_day_ratio20
def test_ratio_and_missing_not_zero():
 v,n,r=up_day_ratio20(pd.Series(range(1,22)));assert v==1 and n==20 and r==1
