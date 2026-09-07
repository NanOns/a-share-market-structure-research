import pandas as pd
from sector.phase2 import rank_sectors,RANKS

def test_rank_type_ties_and_invalid():
    x=pd.DataFrame({'sector_type':['INDUSTRY']*3+['THEME']*2,'sector_role':['INDUSTRY']*3+['THEME','EXCLUDE_FROM_THEME_RANK'],'sector_valid':[True,True,False,True,False]})
    for c in RANKS.values():x[c]=[10,10,100,1,999]
    y=rank_sectors(x)
    assert y.sector_rs20_pct.iloc[:2].tolist()==[.75,.75]
    assert y.sector_rs20_pct.iloc[3]==1
    assert pd.isna(y.sector_rs20_pct.iloc[2]) and pd.isna(y.sector_rs20_pct.iloc[4])
