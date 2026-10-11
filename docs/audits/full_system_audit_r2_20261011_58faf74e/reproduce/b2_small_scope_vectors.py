import sys,json,hashlib,statistics,math
from pathlib import Path
B=Path('G:/codex_tmp/full_system_audit_r2_58faf74e');R=Path('G:/codex work/大A交易');sys.path[:0]=[str(R/'src'),str(R)]
import pandas as pd
from workbench_analysis.full_loo_v3_3 import recompute_full_current_loo
from tests.upgrade_v3.test_p12_12_full_loo import config,frames
from workbench_analysis.fep_e2.conditional import statistics as actual_statistics
checks=[]
def record(name,expected,actual):checks.append(dict(case=name,expected=expected,actual=actual,passed=expected==actual))
for n in (1,2,6):
 values=[.01*(i+1) for i in range(n)];members=pd.DataFrame([dict(sector_id='A',sector_name='A',sector_type='INDUSTRY',sector_role='INDUSTRY',security_id='S'+str(i),trade_date='2026-09-15',ret1=v) for i,v in enumerate(values)])
 market=pd.DataFrame([dict(security_id='S'+str(i),trade_date='2026-09-15',ret1=v) for i,v in enumerate(values)]+[dict(security_id='OUTSIDE',trade_date='2026-09-15',ret1=-.1)])
 try:
  out=recompute_full_current_loo(['S0'],members,market,config())['S0'];details=out['relations'][0]
  record('LOO_N'+str(n)+'_remaining_member_count',n-1,details.get('member_count',0))
  if n==1:record('LOO_N1_empty_relation_unknown','SECTOR_EMPTY_AFTER_EXCLUSION',details.get('reason'))
  else:
   expected=statistics.median(values[1:]+[-.1]);record('LOO_N'+str(n)+'_market_median',expected,details['market_m1']);record('LOO_N'+str(n)+'_sector_median',statistics.median(values[1:]),details['m1'])
 except Exception as e:record('LOO_N'+str(n)+'_no_unhandled_exception',True,type(e).__name__+': '+str(e))
# Negative control: same singleton target with a surviving unrelated sector.
members=pd.DataFrame([dict(sector_id=sec,sector_name=sec,sector_type='INDUSTRY',sector_role='INDUSTRY',security_id=sid,trade_date='2026-09-15',ret1=ret) for sec,sid,ret in [('A','S0',.01),('B','OTHER',.02)]])
market=pd.DataFrame([dict(security_id=sid,trade_date='2026-09-15',ret1=ret) for sid,ret in [('S0',.01),('OTHER',.02),('OUTSIDE',-.1)]])
out=recompute_full_current_loo(['S0'],members,market,config())['S0'];record('LOO_N1_WITH_OTHER_SECTOR_EMPTY_REASON','SECTOR_EMPTY_AFTER_EXCLUSION',out['relations'][0]['reason']);record('LOO_N1_WITH_OTHER_SECTOR_UNKNOWN',None,out['support'])
# Full overlapping cross section exercises the current candidate contract, not formal LOO admission.
members,market=frames();out=recompute_full_current_loo(['S0'],members,market,config())['S0'];record('LOO_OVERLAP_RELATIONS',2,out['tested_relations']);record('LOO_OVERLAP_COUNTS',[5,6],sorted(r['member_count'] for r in out['relations']));record('LOO_OVERLAP_MARKET',statistics.median(market.loc[market.security_id!='S0','ret1']),out['relations'][0]['market_m1'])
# Independent static labels: FIRST categorical is exclusive; ANY events may co-occur.
dates=['2026-09-14','2026-09-14','2026-09-15'];classes=['NONE','EXIT','INVALIDATED'];rows=[dict(observation_id=str(i),trade_date=d,outcome=v) for i,(d,v) in enumerate(zip(dates,['EXIT','NONE','INVALIDATED']))]
first,_=actual_statistics(rows,'CATEGORICAL',classes);record('FIRST_EXCLUSIVE_WEIGHTED_FREQUENCY',dict(NONE=.25,EXIT=.25,INVALIDATED=.5),first['observed_weighted_frequency']);record('FIRST_TOTAL_MASS',1.,sum(first['observed_weighted_frequency'].values()))
rows=[dict(observation_id=str(i),trade_date=d,outcome=v) for i,(d,v) in enumerate(zip(dates,[dict(EXIT=True,INVALIDATED=True),dict(EXIT=False,INVALIDATED=False),dict(EXIT=True,INVALIDATED=True)]))]
any_events,_=actual_statistics(rows,'ANY_EVENTS',['EXIT','INVALIDATED']);record('ANY_COOCCURRENCE_MASS',dict(EXIT=.75,INVALIDATED=.75),any_events['observed_weighted_frequency']);record('ANY_NOT_JOINT_NORMALIZATION',False,any_events['jointly_normalized'])
out=dict(contract='B2_SMALL_LOO_AND_EVENT_FAMILY_STATIC_ORACLE_R2',checks=checks,passed=sum(r['passed'] for r in checks),failed=sum(not r['passed'] for r in checks),limitations=['LOO candidate V3.3 synthetic audit only; no formal PIT or D0 grant.','FIRST/ANY verifies conditional aggregation over fixed labels; historical label generation and risk-set completeness not established.'],sources=[dict(path=p,sha256=hashlib.sha256((R/p).read_bytes()).hexdigest()) for p in ['src/workbench_analysis/full_loo_v3_3.py','src/workbench_analysis/fep_e2/conditional.py']])
(B/'b2_small_scope_vectors.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps(out,ensure_ascii=False))
