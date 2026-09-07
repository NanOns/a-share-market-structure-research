import pandas as pd
from candidates.research_priority import assign_pattern_ranks
def test_pattern_rank(row):
 a=row.copy();b=row.copy();b.update(security_id='SH.600001',stock_rs20_pct=.9);x=assign_pattern_ranks(pd.DataFrame([a,b]));assert x.loc[x.security_id.eq('SH.600001'),'within_pattern_rank_pct'].iloc[0]==1
