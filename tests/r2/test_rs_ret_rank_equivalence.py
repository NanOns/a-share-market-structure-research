import pandas as pd
def test_constant_shift_preserves_average_rank():
    r=pd.Series([.1,.2,.2,.4]);rs=r-.15;assert r.rank(pct=True,method='average').equals(rs.rank(pct=True,method='average'))
