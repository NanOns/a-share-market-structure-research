import pandas as pd
from sector.phase2 import sectors,specs

def test_empty_header_retained_invalid():
    columns={col:pd.Series(dtype=float) for col,_ in specs(True).values()}
    for n in (5,10,20,60):columns[f'RS{n}']=pd.Series(dtype=float)
    columns.update(security_id=pd.Series(dtype='str'),universe_status=pd.Series(dtype='str'),
                   valid_member=pd.Series(dtype=bool),tradable=pd.Series(dtype=bool),missing_state=pd.Series(dtype='str'),RET1=pd.Series(dtype=float))
    stocks=pd.DataFrame(columns)
    membership=pd.DataFrame([dict(sector_type='style',sector_code='empty',sector_name='empty',security_id=None)])
    out,_=sectors(stocks,membership)
    assert len(out)==1 and out.total_member_count.iloc[0]==0
    assert not out.sector_valid.iloc[0]
    assert pd.isna(out.sector_rs20_pct.iloc[0])
