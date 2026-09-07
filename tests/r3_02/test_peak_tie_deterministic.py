import pandas as pd
from shadow_v2.diagnostics import recent_peak20
def test_latest_tie_wins():
 d=pd.date_range("2026-01-01",periods=4)
 assert recent_peak20(d,[1,3,3,2])[0]==d[2]
