import pandas as pd
def test_average_ties(row):
 x=pd.Series([70.0,70.0,50.0]).rank(pct=True,method='average',ascending=True);assert x.iloc[0]==x.iloc[1]
