"""End-to-end scoped event selection → date-equal empirical population check."""
from itertools import permutations
from workbench_analysis.v4_15_settlement import SettlementRuntime
from workbench_analysis.fep_e2.conditional import statistics

class Store:
    def __init__(self,t0):self.t0=t0;self.rows={}
    def read(self,ref):return {'T0':self.t0} if ref=='freeze' else self.rows[ref]
    def append(self,kind,key,row):self.rows[key]=row;return key

def runtime():
    obj=SettlementRuntime.__new__(SettlementRuntime);obj.store=Store('2026-09-15');return obj

def test_first_event_generation_date_then_risk_priority_all_permutations():
    events=[{'trade_date':'2026-09-14','event':'INVALIDATED'},
            {'trade_date':'2026-09-15','event':'CONFIRMED'},
            {'trade_date':'2026-09-15','event':'INVALIDATED'},
            {'trade_date':'2026-09-16','event':'EXPIRED'},
            {'trade_date':'2026-09-17','event':'INVALIDATED'}]
    for values in permutations(events):
        obj=runtime();ref=obj.competing_outcome('freeze',values,'2026-09-16');row=obj.store.read(ref)
        assert row['competing_event']=='INVALIDATED' and row['first_event_trade_date']=='2026-09-15'
        assert row['censoring_state']=='OBSERVED' and row['price_settlement_continues'] is True

def test_right_censor_retained_in_first_population_not_any_normalization():
    rows=[]
    for oid,day,events in [('a','2026-09-15',[]),('b','2026-09-15',[{'trade_date':'2026-09-15','event':'CONFIRMED'}]),('c','2026-09-16',[{'trade_date':'2026-09-16','event':'INVALIDATED'}])]:
        obj=runtime();ref=obj.competing_outcome('freeze',events,'2026-09-16');row=obj.store.read(ref)
        rows.append(dict(observation_id=oid,trade_date=day,outcome=row['competing_event'] or 'NONE'))
    first,_=statistics(rows,'CATEGORICAL',['NONE','CONFIRMED','INVALIDATED','EXPIRED'])
    assert first['observed_weighted_frequency']==dict(NONE=.25,CONFIRMED=.25,INVALIDATED=.5,EXPIRED=0)
    any_rows=[dict(observation_id=r['observation_id'],trade_date=r['trade_date'],outcome=dict(CONFIRMED=True,INVALIDATED=True)) for r in rows]
    any_result,_=statistics(any_rows,'ANY_EVENTS',['CONFIRMED','INVALIDATED'])
    assert any_result['observed_weighted_frequency']==dict(CONFIRMED=1,INVALIDATED=1)
    assert any_result['jointly_normalized'] is False
