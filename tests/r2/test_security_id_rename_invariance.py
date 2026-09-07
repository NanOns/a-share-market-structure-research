import pandas as pd
from candidates.research_priority import score
def test_rename_invariance(priority_rows):
    a=score(pd.DataFrame(priority_rows));priority_rows[0]['security_id']='BJ.430001';b=score(pd.DataFrame(priority_rows));assert a.iloc[0].priority_score==b.iloc[0].priority_score
