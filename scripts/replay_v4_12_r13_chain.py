"""Fresh processes for hand-written paths; expected values never use runtime helpers."""
import json,subprocess,sys
from scripts.v4_11_promotion_contract_r1 import ROOT
OUT='reports/v4_12_runtime_r13/'
BASE=dict(O=11,C=11,H=12,L=11,CLV=.7,ATR20=1,atr_prior_view=1,prior_high20=100,prior_high_view=100,prior_range20_atr=100,amount_ratio20=0,rel_market_1=0,price_basis='SYNTHETIC_QFQ',adjustment_source_revision='SYNTHETIC_REV',evaluable=True)
TRIGGER=dict(prior_high20=10)
# Independent literal oracle. These business results were written before replay.
PATHS={
 'no_event':[('2026-09-23','r1',{},'NO_BREAKOUT',0)],
 'near':[('2026-09-23','r1',dict(near_high20_state='NEAR'),'APPROACHING',0)],
 'unknown_empty':[('2026-09-23','r1',dict(prior_high20=10,evaluable=None),'UNKNOWN',0)],
 'holds':[('2026-09-23','r1',TRIGGER,'BREAKOUT_TENTATIVE',1),('2026-09-24','r1',dict(L=10,CLV=.4),'TESTING',1),('2026-09-28','r1',{},'BREAKOUT_ACCEPTED',1)],
 'retained':[('2026-09-23','r1',TRIGGER,'BREAKOUT_TENTATIVE',1),('2026-09-24','r1',{},'BREAKOUT_TENTATIVE',1)],
 'duplicate':[('2026-09-23','r1',TRIGGER,'BREAKOUT_TENTATIVE',1),('2026-09-24','r1',dict(prior_high20=10,C=12,H=13,L=12),'BREAKOUT_TENTATIVE',1)],
 'display_switch':[('2026-09-23','r1',TRIGGER,'BREAKOUT_TENTATIVE',1),('2026-09-24','r1',dict(O=11,C=12,H=13,L=10,CLV=.7,amount_ratio20=2,rel_market_1=1),'TESTING',1)],
 'terminal':[('2026-09-23','r1',TRIGGER,'BREAKOUT_TENTATIVE',1),('2026-09-24','r1',dict(O=8,C=8,H=8.1,L=8,CLV=.4),'BREAKOUT_TENTATIVE',1),('2026-09-28','r1',dict(O=8,C=8,H=8.1,L=8,CLV=.4),'FAILED_BREAKOUT',1),('2026-09-29','r1',dict(prior_high20=10,C=12,H=13,L=12),'BREAKOUT_TENTATIVE',2)],
 'revisions':[('2026-09-23','r1',TRIGGER,'BREAKOUT_TENTATIVE',1),('2026-09-24','r1',dict(L=10,CLV=.4),'TESTING',1),('2026-09-24','r2',dict(evaluable=None),'UNKNOWN',1),('2026-09-24','r3',{},'BREAKOUT_TENTATIVE',1)]}
CASES={'E01':'no_event/2026-09-23/r1','E02':'near/2026-09-23/r1','E03':'holds/2026-09-23/r1','E04':'retained/2026-09-24/r1','E05':'holds/2026-09-24/r1','E06':'holds/2026-09-28/r1','E07':'terminal/2026-09-28/r1','E08':'terminal/2026-09-29/r1','E09':'duplicate/2026-09-24/r1','E10':'display_switch/2026-09-24/r1','E11':'revisions/2026-09-24/r3','E12':'revisions/2026-09-24/r2'}
def write(path,v):
 p=ROOT/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((json.dumps(v,sort_keys=True,indent=2)+'\n').encode())
def run():
 book={};processes=[]
 for name,steps in PATHS.items():
  predecessors={}
  for date,rev,values,expected,count in steps:
   fixture=OUT+'fixtures/'+name+'/'+date+'/'+rev+'.json';write(fixture,dict(scope='SYNTHETIC_ENGINEERING_ONLY_NO_ACCEPTED_SOURCE_CLAIM',values={**BASE,**values}))
   directory=OUT+'synthetic/'+name+'/'+date+'/'+rev
   cmd=[sys.executable,'-m','scripts.run_v4_12_r13_day','--date',date,'--revision',rev,'--directory',directory,'--fixture',fixture]
   earlier=sorted(d for d in predecessors if d<date);prior=predecessors[earlier[-1]] if earlier else None
   if prior:cmd+=['--prior',prior]
   subprocess.run(cmd,cwd=ROOT,check=True);processes.append(dict(directory=directory,prior=prior,fresh_process=True))
   if rev=='r1':predecessors[date]=directory+'/snapshot_ref.json'
   book[name+'/'+date+'/'+rev]=dict(state=expected,episodes=count)
 previous=None
 for date in ['2026-09-29','2026-09-30']:
  directory=OUT+'real/'+date+'/r1';cmd=[sys.executable,'-m','scripts.run_v4_12_r13_day','--date',date,'--directory',directory]
  if previous:cmd+=['--prior',previous]
  subprocess.run(cmd,cwd=ROOT,check=True);processes.append(dict(directory=directory,prior=previous,fresh_process=True));previous=directory+'/snapshot_ref.json'
 write(OUT+'R13_INDEPENDENT_LITERAL_BOOK.json',dict(expected=book,cases=CASES,oracle='HAND_WRITTEN_NOT_RUNTIME_GENERATED',failure_time_role='PRIOR_SUPPORT_FROZEN_AST'))
 write(OUT+'R13_FRESH_PROCESS_REPLAY.json',dict(status='COMPLETED_NOT_YET_VALIDATED',processes=processes))
if __name__=='__main__':run()
