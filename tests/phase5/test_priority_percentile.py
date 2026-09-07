import pandas as pd
from candidates.research_priority import score
def test_pct(row):
 a=row.copy();b=row.copy();b.update(security_id='SH.600001',primary_pattern='SECTOR_LEADER',sector_leader=True,steady_trend=False,primary_leader_pattern='REACCELERATION');x=score(pd.DataFrame([a,b]));assert x.research_priority_pct.max()==1
