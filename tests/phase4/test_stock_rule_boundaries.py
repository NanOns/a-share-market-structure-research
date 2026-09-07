import pytest
from scanner.stock_scanner import scan_row
@pytest.mark.parametrize('field,value,scanner',[('RET20',0,'steady_trend'),('MDD20',-.15,'steady_trend'),('POS60',.549999,'steady_trend'),('DIST_HIGH20',-.050001,'breakout_prep'),('AMOUNT_RATIO_5_20',.899999,'breakout_prep'),('stock_rs5_pct',.799999,'early_mover')])
def test_boundaries(base,field,value,scanner):
 base.update(DIST_HIGH20=-.04,RET5=.12,has_current_strength_sector=False,leader_eligible=False);base[field]=value;assert not scan_row(base)[scanner]
