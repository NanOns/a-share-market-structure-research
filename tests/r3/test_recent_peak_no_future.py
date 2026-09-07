import pandas as pd
from shadow_v2.diagnostics import recent_peak20
def test_peak_uses_supplied_past_only():
 d=pd.date_range('2026-01-01',periods=20);assert recent_peak20(d,list(range(20)))[1]==19
