import pytest
@pytest.fixture
def row():
 return dict(security_id='SH.600000',in_normal_universe=True,tradable=True,quality_flag='OK',steady_trend=True,strong_pullback=False,breakout_prep=False,sector_leader=False,early_mover=False,primary_pattern='STEADY_TREND',scanner_hits='STEADY_TREND',warning_codes='',has_reacceleration_sector=False,has_current_strength_sector=False,has_stabilization_sector=False,best_sector_rs20_pct=.5,primary_member_rs20_pct=.5,stock_rs20_pct=.5,stock_rs60_pct=.5,stock_rs5_pct=.5,DIST_HIGH20=-.1,TREND_R2_20=.6,MDD20=-.1,RS20=.1,AMOUNT_RATIO_5_20=1,RET5=.1,leader_sector_count=1,valid_sector_count=1)
