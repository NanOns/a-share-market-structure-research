import pandas as pd
from scanner.sector_scanner import scan

def test_invalid_and_excluded_absent(strong):
    rows=[]
    for i,(valid,role) in enumerate([(True,'THEME'),(False,'THEME'),(False,'EXCLUDE_FROM_THEME_RANK')]):
      r=strong|{'sector_id':str(i),'sector_name':str(i),'sector_type':'THEME','sector_valid':valid,'sector_role':role,
        'sector_rs5':i,'sector_rs20':i,'sector_rs60':i,'sector_rs20_pct':1,'tradable_member_count':10,'date':pd.Timestamp('2026-09-04')}
      rows.append(r)
    out=scan(pd.DataFrame(rows))
    assert out.sector_id.tolist()==['0']
