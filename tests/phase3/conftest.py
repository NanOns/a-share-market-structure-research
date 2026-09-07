import pytest

@pytest.fixture
def strong():
    return dict(sector_valid=True,coverage=.9,valid_member_count=10,sector_role='THEME',
      sector_ret5_median=.03,sector_ret20_median=.10,sector_ret60_median=.20,
      sector_rs5_pct=.9,sector_rs20_pct=.9,sector_rs60_pct=.9,
      sector_breadth_ret5_pos=.75,sector_breadth_ret20_pos=.65,sector_breadth_ret60_pos=.6,
      sector_pos60_median=.8,sector_dist_high20_median=-.04,sector_mdd20_median=-.05,
      sector_amount_ratio_median=1.2,top3_concentration=.3,
      breadth_5_20_common_valid_count=9,breadth_5_20_common_valid_ratio=.9,
      breadth_ret5_pos_common=.75,breadth_ret20_pos_common=.65,breadth_5_minus_20_common=.10,
      current_strength_joint_valid_count=9,current_strength_joint_valid_ratio=.9,
      stabilization_joint_valid_count=9,stabilization_joint_valid_ratio=.9,
      reacceleration_joint_valid_count=9,reacceleration_joint_valid_ratio=.9,
      **{f+'__valid_count':9 for f in ('sector_ret5_median','sector_ret20_median','sector_ret60_median','sector_rs5','sector_rs20','sector_rs60','sector_breadth_ret20_pos','sector_pos60_median','sector_dist_high20_median','sector_mdd20_median','sector_amount_ratio_median')},
      **{f+'__valid_ratio':.9 for f in ('sector_ret5_median','sector_ret20_median','sector_ret60_median','sector_rs5','sector_rs20','sector_rs60','sector_breadth_ret20_pos','sector_pos60_median','sector_dist_high20_median','sector_mdd20_median','sector_amount_ratio_median')})
