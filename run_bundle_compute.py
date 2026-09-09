from __future__ import annotations
import argparse,json,os,shutil,sys,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT/"src"))
from workbench_input import verify_source_bundle
from production.daily import run_daily
from run_live_forward import ProductionServices
def link_tree(source,dest):
 for p in source.rglob("*"):
  target=dest/p.relative_to(source)
  if p.is_dir():target.mkdir(parents=True,exist_ok=True)
  else:target.parent.mkdir(parents=True,exist_ok=True);os.link(p,target)
def main():
 a=argparse.ArgumentParser();a.add_argument("--bundle-id",required=True);a.add_argument("--date",required=True);x=a.parse_args();bp=ROOT/"data/source_bundles"/x.bundle_id/"source_bundle.json";verify_source_bundle(bp);body=json.loads(bp.read_text("utf-8"))
 if body["target_trade_date"].replace("-","")!=x.date:raise ValueError("BUNDLE_TRADE_DATE_MISMATCH")
 view=ROOT/"data/input_staging/compute_views"/(x.date+"-"+uuid.uuid4().hex)
 try:
  (view/"vipdoc").mkdir(parents=True);link_tree(ROOT/body["extraction"]["root"],view/"vipdoc");link_tree(ROOT/body["metadata"]["root"]/"T0002",view/"T0002")
  code,result=run_daily(ROOT,view,"latest",False,False)
  if code:raise RuntimeError("DAILY_PIPELINE_FAILED:"+json.dumps(result,ensure_ascii=False))
  pointer=json.loads((ROOT/"reports/current"/(x.date+".json")).read_text("utf-8"))
  pointer_date=str(pointer.get("cutoff_date") or pointer.get("date") or "").replace("-","")
  if pointer_date!=x.date:raise ValueError("COMPUTE_CUTOFF_MISMATCH")
  release=Path(pointer["release_path"]);receipt=json.loads((release/"PRODUCTION_RECEIPT.json").read_text("utf-8"))
  if str(receipt.get("cutoff_date") or "").replace("-","")!=x.date:raise ValueError("COMPUTE_RELEASE_CUTOFF_MISMATCH")
  # M4 publishes the five-queue workbench, not merely the V1 daily release.
  # Build the date-aligned V2 artifacts and ranking before the publisher reads
  # them; otherwise a fresh trading date has no V2_QUEUE_RANKING.parquet.
  v1={"published_release_id":pointer["run_id"],"run_id":pointer["run_id"],"resolved_cutoff_date":x.date}
  services=ProductionServices();statuses,_=services.run_v2(ROOT,x.date,v1)
  workbench=services.publish_workbench(ROOT,x.date,v1,statuses)
  if not Path(workbench["path"]).is_file() or not (Path(workbench["path"]).parent/"V2_QUEUE_RANKING.parquet").is_file():
   raise ValueError("V2_WORKBENCH_RANKING_MISSING")
  print(json.dumps({"release_path":pointer["release_path"],"run_id":pointer["run_id"]},ensure_ascii=False));return 0
 finally:shutil.rmtree(view,ignore_errors=True)
if __name__=="__main__":raise SystemExit(main())
