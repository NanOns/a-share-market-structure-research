"""Build and verify the complete daily V3.3 research package after publication."""
from __future__ import annotations
import argparse,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from workbench_service.research_bundle_v3_3 import read_active

STAGES=['p12_03_current_funnel.py','p12_04_current_loo_probe.py','p12_04_current_rank_probe.py','build_p12_06_candidate_bundle.py','build_p12_08e_enriched_bundle.py','run_p12_08_forward_observation.py','run_p12_08b_outcome_plan.py','run_p12_08c_outcome_materialization.py']
POINTER=ROOT/'data/current/ACTIVE_RESEARCH_BUNDLE_V3_3.json'
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--publication-id',required=True);parser.add_argument('--trade-date',required=True);args=parser.parse_args()
 active=read_active(POINTER);enriched=False
 if active:
  try:
   rows=json.loads((Path(active['bundle_path'])/'results.json').read_text(encoding='utf-8'));enriched=not rows or all(row.get('security_name') and 'scanner_evidence' in row for row in rows)
  except Exception:enriched=False
 if active and enriched and active['identity'].get('publication_id')==args.publication_id and active['identity'].get('trade_date')==args.trade_date:
  print(json.dumps({'status':'READY','reused':True,'publication_id':args.publication_id,'trade_date':args.trade_date,'bundle_digest':active['output_digest'],'completed_stages':[]},ensure_ascii=False));return
 completed=[]
 for name in STAGES:
  result=subprocess.run([sys.executable,str(ROOT/'scripts'/name)],cwd=ROOT,capture_output=True,text=True)
  if result.returncode:raise SystemExit(json.dumps({'status':'FAILED','stage':name,'stderr':result.stderr[-2000:],'stdout':result.stdout[-2000:]},ensure_ascii=False))
  completed.append(name)
 active=read_active(POINTER)
 if not active or active['identity'].get('publication_id')!=args.publication_id or active['identity'].get('trade_date')!=args.trade_date:raise SystemExit('V3_3_ACTIVE_IDENTITY_MISMATCH')
 print(json.dumps({'status':'READY','reused':False,'publication_id':args.publication_id,'trade_date':args.trade_date,'bundle_digest':active['output_digest'],'completed_stages':completed},ensure_ascii=False))
if __name__=='__main__':main()
