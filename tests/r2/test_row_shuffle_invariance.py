import pandas as pd
from candidates.research_priority import score
def test_shuffle_invariance(priority_rows):
    f=pd.DataFrame(priority_rows);a=score(f).set_index('security_id').priority_score;b=score(f.sample(frac=1,random_state=7)).set_index('security_id').priority_score;assert a.sort_index().equals(b.sort_index())
