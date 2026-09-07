from shadow_v2.sector_leader import choose_primary
def test_price_style_loses_to_economic():
 a={"sector_semantic":"PRICE_BEHAVIOR_STYLE","reacceleration":True,"sector_rs20_pct":1,"member_rs20_pct":1,"sector_id":"STYLE:1"};b={"sector_semantic":"ECONOMIC_SECTOR","reacceleration":False,"sector_rs20_pct":.8,"member_rs20_pct":.8,"sector_id":"INDUSTRY:1"};assert choose_primary([a,b]) is b
