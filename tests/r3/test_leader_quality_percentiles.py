import pandas as pd
from shadow_v2.diagnostics import quality_percentiles
def test_directions():
 f=pd.DataFrame({'sector_id':['x','x'],'TREND_R2_20':[.2,.8],'MDD20':[-.2,-.1],'POS60':[.2,.8],'RETURN_CONCENTRATION_20':[.8,.2]});x=quality_percentiles(f);assert x.iloc[1].member_mdd20_quality_pct>x.iloc[0].member_mdd20_quality_pct and x.iloc[1].member_return_concentration_quality_pct>x.iloc[0].member_return_concentration_quality_pct
