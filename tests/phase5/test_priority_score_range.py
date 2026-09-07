import pandas as pd
from candidates.research_priority import score
def test_range(row):assert score(pd.DataFrame([row])).priority_score.between(0,100).all()
