from shadow_v2.sector_leader import choose_primary
def test_one_relation_returned():
 r={"sector_semantic":"ECONOMIC_SECTOR","reacceleration":True,"sector_rs20_pct":.9,"member_rs20_pct":.9,"sector_id":"A"};assert choose_primary([r])==r
