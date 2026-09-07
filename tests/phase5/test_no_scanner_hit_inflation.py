import pandas as pd
from candidates.research_priority import score
def test_hits_not_scored(row):
 a=score(pd.DataFrame([row])).priority_score.iloc[0];row['scanner_hits']='STEADY_TREND|STRONG_PULLBACK';b=score(pd.DataFrame([row])).priority_score.iloc[0];assert a==b
