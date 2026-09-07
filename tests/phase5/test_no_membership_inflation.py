import pandas as pd
from candidates.research_priority import score
def test_memberships_not_scored(row):
 a=score(pd.DataFrame([row])).priority_score.iloc[0];row['valid_sector_count']=5;b=score(pd.DataFrame([row])).priority_score.iloc[0];assert a==b
