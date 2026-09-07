import pytest

@pytest.fixture
def base():
 return dict(security_id='SH.600000',universe_status='IN_NORMAL_UNIVERSE',tradable=True,latest_factor_row=True,fatal_quality_error=False,
 RET5=.03,RET20=.10,RET60=.20,RS5=.02,RS20=.03,RS60=.04,TREND_SLOPE_20=.01,TREND_SLOPE_60=.01,TREND_R2_20=.60,TREND_R2_60=.50,
 POS20=.80,POS60=.70,MDD20=-.10,MDD60=-.20,DIST_HIGH20=-.10,DIST_HIGH60=-.09,VOLATILITY20=.02,MA20=10,MA60=9,adj_close=11,
 AMOUNT_RATIO_5_20=1.0,stock_rs5_pct=.9,has_current_strength_sector=True,has_reacceleration_sector=False,leader_eligible=True,leader_sector_count=1,
 primary_leader_high_concentration=False,primary_leader_low_coverage=False)
