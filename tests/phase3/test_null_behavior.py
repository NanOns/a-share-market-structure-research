import numpy as np
from scanner.sector_scanner import scan_row

def test_required_null_fails_and_concentration_is_unavailable(strong):
    strong['sector_rs20_pct']=np.nan; strong['top3_concentration']=np.nan
    row=scan_row(strong)
    assert not row['current_strength'] and not row['high_concentration']
    assert row['concentration_tag_status']=='UNAVAILABLE'
