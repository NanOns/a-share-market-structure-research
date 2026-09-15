"""Join P12-03 stock hits with P12-04 LOO and verify uncapped ranking."""
from __future__ import annotations
import json,os,sys,tempfile
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from workbench_analysis.today_research_rank_loo_v3_3 import rank,simple_shadow
OUT=ROOT/'reports/p12_04/current_rank_probe.json'
def main():
 f=json.loads((ROOT/'reports/p12_03/current_funnel.json').read_text(encoding='utf-8'));l=json.loads((ROOT/'reports/p12_04/current_loo_probe.json').read_text(encoding='utf-8'));audits=l['stock_support_audit'];rows=[];observations=0
 for x in f['eligible_or_watch_rows']:
  support=audits.get(x['security_id'],{}).get('support');matched=[c for c in x['matched_stock_only_categories'] if c!='TREND_CONTINUE' or support is True]
  if matched:
   rows.append({**x,'matched_categories':matched,'selection_mode':'SUPPORTED' if support is True else 'INDEPENDENT','sector_support_status':'CONFIRMED' if support is True else 'UNKNOWN' if support is None else 'NOT_CONFIRMED','signal_age':None})
  elif x['setup_watch'] is True:observations+=1
 ranked=rank(rows);simple=simple_shadow(ranked);primary=Counter(x['primary_category'] for x in ranked);modes=Counter(x['selection_mode'] for x in ranked);scored=sum(x['category_score'] is not None for x in ranked);unscored=len(ranked)-scored
 result={'stage_contract':'P12-04_CURRENT_RANK_PROBE_V1','captured_at_utc':datetime.now(timezone.utc).isoformat(),'input_identity':l['input_identity'],'qualified_unique_stocks':len(ranked),'primary_category_counts':dict(primary),'selection_mode_counts':dict(modes),'scored':scored,'qualified_unranked':unscored,'setup_watch_observations':observations,'stock_only_trend_true':f['scenario_counts']['trend_continue_stock_only'].get('True',0),'formal_trend_after_loo':primary.get('TREND_CONTINUE',0),'complex_and_simple_same_sample':{x['security_id'] for x in ranked}=={x['security_id'] for x in simple},'qualification_cap_applied':False,'ranked_rows':ranked,'simple_shadow_first20':[x['security_id'] for x in simple[:20]],'acceptance_result':'DEGRADED_PASS','next_stage':'P12-04_RANK_AND_LOO_V3_3_CONTINUE'}
 if not result['complex_and_simple_same_sample'] or len(ranked)!=len({x['security_id'] for x in ranked}):result.update(acceptance_result='BLOCKED',next_stage='P12-04_REPAIR')
 OUT.parent.mkdir(parents=True,exist_ok=True);fd,tmp=tempfile.mkstemp(dir=OUT.parent)
 try:
  with os.fdopen(fd,'w',encoding='utf-8') as s:json.dump(result,s,ensure_ascii=False,indent=2);s.write('\n');s.flush();os.fsync(s.fileno())
  os.replace(tmp,OUT)
 finally:
  if os.path.exists(tmp):os.unlink(tmp)
 if result['acceptance_result']=='BLOCKED':raise RuntimeError('rank probe blocked')
 print(OUT)
if __name__=='__main__':main()
