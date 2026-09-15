"""Verify bounded P12-04 LOO/rank acceptance evidence."""
from __future__ import annotations
import hashlib,json,os,sys,tempfile
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from workbench_analysis.today_research_rank_loo_v3_3 import CONTRACT_ID
OUT=ROOT/'reports/p12_04/p12_04_stage_gate.json'
def load(n):return json.loads((ROOT/'reports'/n).read_text(encoding='utf-8'))
def sha(p):h=hashlib.sha256();h.update(p.read_bytes());return h.hexdigest()
def main():
 prior=load('p12_03/p12_03_stage_gate.json');loo=load('p12_04/current_loo_probe.json');rank=load('p12_04/current_rank_probe.json')
 checks={'p12_03_accepted':prior['acceptance_result']=='DEGRADED_PASS','real_relation_edges_present':loo['unique_edges']>0 and loo['stocks_with_relations']>0,'six_real_stock_cases':len(loo['six_real_stock_cases'])==6,'relationship_bands_reconcile':sum(sum(x.values()) for x in loo['relationship_band_support'].values())==loo['stocks_with_relations'],'stock_only_shadow_preserved':rank['stock_only_trend_true']>=rank['formal_trend_after_loo']>0,'qualified_unique_uncapped':rank['qualified_unique_stocks']==sum(rank['primary_category_counts'].values()) and rank['qualification_cap_applied'] is False,'unscored_qualified_retained':rank['qualified_unranked']>0,'scored_population_present':rank['scored']>0,'simple_shadow_same_sample':rank['complex_and_simple_same_sample'],'historic_change_loo_not_fabricated':loo['historical_change_loo_status']=='UNKNOWN_HISTORIC_MEMBERSHIP'}
 result={'stage_contract':'P12-04_RANK_AND_LOO_V3_3_ACCEPTANCE_V1','captured_at_utc':datetime.now(timezone.utc).isoformat(),'contract_id':CONTRACT_ID,'source_sha256':sha(ROOT/'src/workbench_analysis/today_research_rank_loo_v3_3.py'),'input_identity':loo['input_identity'],'checks':checks,'acceptance_result':'DEGRADED_PASS' if all(checks.values()) else 'BLOCKED','acceptance_scope':'Current LOO, relationship audit, support modes, fixed primary category, bounded scores, unscored retention and simple shadow; historic change LOO unavailable','next_stage':'P12-05_REPLAY_V3_3' if all(checks.values()) else 'P12-04_REPAIR'}
 OUT.parent.mkdir(parents=True,exist_ok=True);fd,tmp=tempfile.mkstemp(dir=OUT.parent)
 try:
  with os.fdopen(fd,'w',encoding='utf-8') as s:json.dump(result,s,ensure_ascii=False,indent=2);s.write('\n');s.flush();os.fsync(s.fileno())
  os.replace(tmp,OUT)
 finally:
  if os.path.exists(tmp):os.unlink(tmp)
 if result['acceptance_result']=='BLOCKED':raise RuntimeError('P12-04 blocked')
 print(OUT)
if __name__=='__main__':main()
