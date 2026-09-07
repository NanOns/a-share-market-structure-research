from shadow_v2.sector_leader import choose_primary
def test_reacceleration_then_rs_then_id():
 def r(i,re,rs):return {"sector_semantic":"ECONOMIC_SECTOR","reacceleration":re,"sector_rs20_pct":rs,"member_rs20_pct":.8,"sector_id":i}
 assert choose_primary([r("THEME:1",False,1),r("INDUSTRY:1",True,.7)])["sector_id"]=="INDUSTRY:1"
