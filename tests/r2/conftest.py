import pytest

@pytest.fixture
def sector_row():
    fields=('sector_ret5_median','sector_ret20_median','sector_ret60_median','sector_rs5','sector_rs20','sector_rs60','sector_breadth_ret20_pos','sector_pos60_median','sector_dist_high20_median','sector_mdd20_median','sector_amount_ratio_median')
    row=dict(sector_valid=True,coverage=1.0,valid_member_count=8,sector_role='THEME',sector_ret5_median=.03,sector_ret20_median=.10,sector_ret60_median=.20,sector_rs5=.03,sector_rs20=.10,sector_rs60=.20,sector_rs5_pct=.9,sector_rs20_pct=.9,sector_rs60_pct=.9,sector_breadth_ret5_pos=.75,sector_breadth_ret20_pos=.65,sector_breadth_ret60_pos=.6,sector_pos60_median=.8,sector_dist_high20_median=-.04,sector_mdd20_median=-.05,sector_amount_ratio_median=1.2,top3_concentration=.3,breadth_5_20_common_valid_count=8,breadth_5_20_common_valid_ratio=1.0,breadth_ret5_pos_common=.75,breadth_ret20_pos_common=.65,breadth_5_minus_20_common=.10,current_strength_joint_valid_count=8,current_strength_joint_valid_ratio=1.0,stabilization_joint_valid_count=8,stabilization_joint_valid_ratio=1.0,reacceleration_joint_valid_count=8,reacceleration_joint_valid_ratio=1.0)
    row.update({f+'__valid_count':8 for f in fields});row.update({f+'__valid_ratio':1.0 for f in fields});return row

@pytest.fixture
def priority_rows():
    base=dict(in_normal_universe=True,tradable=True,quality_flag='OK',steady_trend=True,strong_pullback=False,breakout_prep=False,sector_leader=False,early_mover=False,primary_pattern='STEADY_TREND',scanner_hits='STEADY_TREND',warning_codes='',has_reacceleration_sector=False,has_current_strength_sector=False,has_stabilization_sector=False,best_sector_rs20_pct=.5,primary_member_rs20_pct=.5,stock_rs20_pct=.5,stock_rs60_pct=.5,stock_rs5_pct=.5,DIST_HIGH20=-.1,TREND_R2_20=.6,MDD20=-.1,RS20=.1,AMOUNT_RATIO_5_20=1,RET5=.1,leader_sector_count=1,valid_sector_count=1)
    return [{**base,'security_id':'SH.600000'},{**base,'security_id':'SZ.000001'}]
