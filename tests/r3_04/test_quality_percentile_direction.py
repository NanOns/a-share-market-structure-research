import pandas as pd
from shadow_v2.diagnostics import quality_percentiles
def test_directions():
 x=pd.DataFrame({"sector_id":["A"]*2,"TREND_R2_20":[.2,.8],"MDD20":[-.2,-.1],"POS60":[.2,.8],"RETURN_CONCENTRATION_20":[.8,.2]});y=quality_percentiles(x)
 assert all(y.iloc[1][c]>y.iloc[0][c] for c in ("member_trend_r2_20_pct","member_mdd20_quality_pct","member_pos60_pct","member_return_concentration_quality_pct"))
