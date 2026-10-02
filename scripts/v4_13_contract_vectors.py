"""Independent, hand-authored contract witnesses. No implementation expected helper."""
VECTORS=[
 dict(id='L01',input=dict(target='s',returns={'s':100,'a':1,'b':2,'c':3,'d':4,'e':5},seeds={'s':True,'a':False,'b':False,'c':False,'d':False,'e':False}),expected=dict(loo_median=3,seed_k=0,member_n=5,excluded='s')),
 dict(id='L02',input=dict(members=['s','a','b','c','d'],target='s'),expected=dict(remaining=4,quality='UNKNOWN_INSUFFICIENT_LOO_MEMBERS')),
 dict(id='L03',input=dict(industries=[dict(id='I2',priority=1,depth=2),dict(id='I1',priority=1,depth=2)],concepts=['C10','C09','C08','C07','C06','C05','C04','C03','C02','C01']),expected=dict(primary='I1',concepts=['C01','C02','C03','C04','C05','C06','C07','C08','C09','C10'],display=['C01','C02','C03','C04','C05','C06','C07','C08'])),
 dict(id='L04',input=dict(membership=None),expected=dict(value='UNKNOWN',missing_is_false=False)),
 dict(id='L05',input=dict(complete=True,candidates=[]),expected=dict(value=None,quality='NOT_APPLICABLE')),
 dict(id='L06',input=dict(basis='CURRENT_MEMBERSHIP_REPLAY',historical=True),expected=dict(value='DEGRADED',pit=False,formal_context_eligible=False)),
 dict(id='L07',input=dict(rps5=60,rps20=60,rps20_delta3=0,rel_market_1=-2,rel_market_5=-2,rel_sector_1=2,rel_sector_5=2,compression_state='NORMAL',ma_structure_state='OTHER'),expected=dict(relative_sector_state='PASSIVE_RESILIENCE',owner_contract='RELATIVE_STATE_V1')),
 dict(id='L08',input=dict(raw_A=True,raw_C=False,context_before='WEAK',context_after='STRONG'),expected=dict(raw_A=True,raw_C=False)),
 dict(id='L09',input=dict(B0='WARM',B1='STABLE',B2='UNKNOWN',structure_before='IDLE',structure_after='HELD_CONFIRMED'),expected=dict(B0='WARM',B1='STABLE',B2='UNKNOWN')),
 dict(id='L10',input=dict(source_before={'active_anchor_id':'A','basic_breakout_state':'TESTING'},source_after={'active_anchor_id':'B','basic_breakout_state':'TESTING'}),expected=dict(projected_before={'active_anchor_id':'A','basic_breakout_state':'TESTING'},projected_after={'active_anchor_id':'B','basic_breakout_state':'TESTING'},recompute=False)),
 dict(id='L11',input=dict(date='2026-09-30',calendar=['2026-09-24','2026-09-28','2026-09-29','2026-09-30'],revisions=['r1','r2','r3']),expected=dict(predecessors=['2026-09-29','2026-09-29','2026-09-29'])),
 dict(id='L12',input=dict(old={'revision':'r1','members':['a','b']},correction={'revision':'r2','members':['a','c']}),expected=dict(old={'revision':'r1','members':['a','b']},new={'revision':'r2','members':['a','c']},append_only=True))]
