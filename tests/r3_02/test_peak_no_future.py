import pandas as pd
from shadow_v2.diagnostics import recent_peak20
def test_future_peak_does_not_change_cutoff_result():
 d=pd.date_range("2026-01-01",periods=4);c=[1,3,2,9]
 assert recent_peak20(d[:3],c[:3])[:3]==(d[1],3.0,1)
