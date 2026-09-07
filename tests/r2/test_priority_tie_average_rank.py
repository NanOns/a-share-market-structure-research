import pandas as pd
from candidates.research_priority import assign_pattern_ranks
def test_average_rank(priority_rows):
    x=assign_pattern_ranks(pd.DataFrame(priority_rows));assert set(x.within_pattern_rank_pct)=={.75}
