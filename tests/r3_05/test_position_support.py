from shadow_v2.early_mover import position_support
def test_position():assert position_support(.6)=="POSITION_HEALTHY" and position_support(.59)=="POSITION_NOT_CONFIRMED"
