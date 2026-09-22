"""Build and verify the complete daily V3.3 research package after publication."""
from __future__ import annotations
import argparse,json,os,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from workbench_service.research_bundle_v3_3 import atomic_write,read_active

STAGES=['p12_03_current_funnel.py','p12_04_current_loo_probe.py','p12_04_current_rank_probe.py','build_p12_06_candidate_bundle.py','build_p12_08e_enriched_bundle.py','run_p12_12_full_loo.py','build_p12_12_full_loo_bundle.py','run_p12_08_forward_observation.py','run_p12_08b_outcome_plan.py','run_p12_08c_outcome_materialization.py']
POINTER=ROOT/'data/current/ACTIVE_RESEARCH_BUNDLE_V3_3.json'
def optional_turnover(publication_id,trade_date):
 try:result=subprocess.run([sys.executable,str(ROOT/'scripts/run_p12_14_daily_turnover.py'),'--publication-id',publication_id,'--trade-date',trade_date],cwd=ROOT,capture_output=True,text=True,timeout=30)
 except Exception as exc:return {'status':'OPTIONAL_DEGRADED','reason':type(exc).__name__,'local_pipeline_blocked':False}
 try:return json.loads(result.stdout.strip().splitlines()[-1])
 except Exception:return {'status':'OPTIONAL_DEGRADED','reason':'OPTIONAL_REPORT_INVALID','local_pipeline_blocked':False}
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--publication-id',required=True);parser.add_argument('--trade-date',required=True);args=parser.parse_args()
 active=read_active(POINTER);enriched=False
 if active:
  try:
   rows=json.loads((Path(active['bundle_path'])/'results.json').read_text(encoding='utf-8'));enriched=not rows or all(row.get('security_name') and 'scanner_evidence' in row for row in rows)
  except Exception:enriched=False
 if active and enriched and active.get('contract_id')=='TODAY_RESEARCH_BUNDLE_V3_3_CANDIDATE_03_FULL_LOO' and active['identity'].get('publication_id')==args.publication_id and active['identity'].get('trade_date')==args.trade_date:
  optional=optional_turnover(args.publication_id,args.trade_date)
  print(json.dumps({'status':'READY','reused':True,'publication_id':args.publication_id,'trade_date':args.trade_date,'bundle_digest':active['output_digest'],'completed_stages':[],'optional_enhancements':{'turnover':optional}},ensure_ascii=False));return
 completed=[];previous_pointer=POINTER.read_bytes() if POINTER.is_file() else None;env={**os.environ,'P12_EXPECTED_PUBLICATION_ID':args.publication_id,'P12_EXPECTED_TRADE_DATE':args.trade_date}
 for name in STAGES:
  result=subprocess.run([sys.executable,str(ROOT/'scripts'/name)],cwd=ROOT,capture_output=True,text=True,env=env)
  if result.returncode:
   if previous_pointer is not None:atomic_write(POINTER,previous_pointer)
   elif POINTER.exists():POINTER.unlink()
   raise SystemExit(json.dumps({'status':'FAILED','stage':name,'stderr':result.stderr[-2000:],'stdout':result.stdout[-2000:],'active_pointer_rolled_back':True},ensure_ascii=False))
  completed.append(name)
 active=read_active(POINTER)
 if not active or active['identity'].get('publication_id')!=args.publication_id or active['identity'].get('trade_date')!=args.trade_date:
  if previous_pointer is not None:atomic_write(POINTER,previous_pointer)
  elif POINTER.exists():POINTER.unlink()
  raise SystemExit('V3_3_ACTIVE_IDENTITY_MISMATCH')
 optional=optional_turnover(args.publication_id,args.trade_date)
 print(json.dumps({'status':'READY','reused':False,'publication_id':args.publication_id,'trade_date':args.trade_date,'bundle_digest':active['output_digest'],'completed_stages':completed,'optional_enhancements':{'turnover':optional}},ensure_ascii=False))
if __name__=='__main__':main()
