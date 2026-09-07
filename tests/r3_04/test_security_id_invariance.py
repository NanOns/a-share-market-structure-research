from shadow_v2.sector_leader import choose_primary
def test_security_id_not_used():
 r={"sector_semantic":"ECONOMIC_SECTOR","reacceleration":True,"sector_rs20_pct":.9,"member_rs20_pct":.9,"sector_id":"A"};a=dict(r,security_id="X");b=dict(r,security_id="Y");assert choose_primary([a])["sector_id"]==choose_primary([b])["sector_id"]
