import pandas as pd
from scanner.sector_scanner import add_percentiles

def test_type_isolation_and_average_ties():
    f=pd.DataFrame({'sector_type':['INDUSTRY','INDUSTRY','THEME','THEME'],
      'sector_valid':[True]*4,'sector_role':['INDUSTRY','INDUSTRY','THEME','THEME'],
      'sector_rs5':[1,1,1,3],'sector_rs20':[1,1,1,3],'sector_rs60':[1,1,1,3]})
    out=add_percentiles(f)
    assert out.sector_rs5_pct.tolist()==[.75,.75,.5,1]
