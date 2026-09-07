import pandas as pd
from candidates.research_priority import score
def test_equal_economic_input_equal_score(priority_rows):
    x=score(pd.DataFrame(priority_rows));assert x.priority_score.nunique()==1 and x.research_priority.nunique()==1
