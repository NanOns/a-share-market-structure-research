"""Verify P12-03 scanner evidence without writing production data."""
from __future__ import annotations
import hashlib,json,os,sys,tempfile
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from workbench_analysis.today_research_scanner_v3_3 import CONTRACT_ID,PARAMETER_CONTRACT
FUNNEL=ROOT/'reports/p12_03/current_funnel.json';OUT=ROOT/'reports/p12_03/p12_03_stage_gate.json';SPEC=ROOT/'docs/V3_TODAY_RESEARCH_PRIORITY_DETAILED_UPGRADE_PLAN_20260914.md'
def sha(p):h=hashlib.sha256();h.update(p.read_bytes());return h.hexdigest()
def main():
 f=json.loads(FUNNEL.read_text(encoding='utf-8')); counts=f['scenario_counts']; total=f['stocks']
 checks={'phase0_and_p12_02_accepted':json.loads((ROOT/'reports/p12_02/p12_02_stage_gate.json').read_text(encoding='utf-8'))['acceptance_result']=='DEGRADED_PASS','full_funnel_reconciles':total==6182 and all(sum(v.values())==total for v in counts.values()),'launch_has_real_true_population':counts['launch'].get('True',0)>0,'setup_watch_has_real_true_population':counts['setup_watch'].get('True',0)>0,'stock_only_continue_preserved':counts['trend_continue_stock_only'].get('True',0)>0,'unsupported_continue_not_promoted':counts['trend_continue'].get('True',0)==0,'missing_pit_not_promoted':counts['pullback'].get('True',0)==0 and counts['recovery_turn'].get('True',0)==0}
 result={'stage_contract':'P12-03_SCANNER_V3_3_ACCEPTANCE_V1','captured_at_utc':datetime.now(timezone.utc).isoformat(),'consulted_spec_sha256':sha(SPEC),'scanner_contract':CONTRACT_ID,'parameter_contract':PARAMETER_CONTRACT,'input_identity':f['input_identity'],'scanner_source_sha256':sha(ROOT/'src/workbench_analysis/today_research_scanner_v3_3.py'),'checks':checks,'funnel':counts,'capability_limits':f['limitations'],'acceptance_result':'DEGRADED_PASS' if all(checks.values()) else 'BLOCKED','acceptance_scope':'Four independent eligibility scenarios, STOCK_ONLY continuation shadow, SETUP_WATCH and explainable tri-state funnel; P12-04 LOO and historic PIT excluded','next_stage':'P12-04_RANK_AND_LOO_V3_3' if all(checks.values()) else 'P12-03_REPAIR'}
 OUT.parent.mkdir(parents=True,exist_ok=True);fd,tmp=tempfile.mkstemp(dir=OUT.parent)
 try:
  with os.fdopen(fd,'w',encoding='utf-8') as s:json.dump(result,s,ensure_ascii=False,indent=2,allow_nan=False);s.write('\n');s.flush();os.fsync(s.fileno())
  os.replace(tmp,OUT)
 finally:
  if os.path.exists(tmp):os.unlink(tmp)
 if result['acceptance_result']=='BLOCKED':raise RuntimeError('P12-03 blocked')
 print(OUT)
if __name__=='__main__':main()
