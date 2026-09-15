from __future__ import annotations
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"src"))
from workbench_analysis.forward_v3_3 import CONTRACT_ID,atomic_write,build_observation,report,seal
from workbench_service.research_bundle_v3_3 import read_active

def main():
 active=read_active(ROOT/"data/current/ACTIVE_RESEARCH_BUNDLE_V3_3.json")
 if not active:raise SystemExit("ACTIVE_BUNDLE_NOT_BUILT")
 results=json.loads((Path(active["bundle_path"])/"results.json").read_text(encoding="utf-8"))
 loo=json.loads((ROOT/"reports/p12_04/current_loo_probe.json").read_text(encoding="utf-8"));relations=loo["stock_support_audit"]
 observations=[]
 for path in sorted((ROOT/"data/forward_v3_3/observations").glob("*/*.json")):
  value=json.loads(path.read_text(encoding="utf-8"))
  if value.get("contract_id")==CONTRACT_ID:observations.append(value)
 previous=max((value for value in observations if value["trade_date"]<active["identity"]["trade_date"]),key=lambda value:value["trade_date"],default=None)
 observation=build_observation(active,results,relations,previous);sealed=seal(ROOT/"data/forward_v3_3/observations",observation)
 observations=[value for value in observations if value["trade_date"]!=observation["trade_date"]]+[observation]
 result=report(observations);report_path=ROOT/"reports/p12_08/forward_report.json";atomic_write(report_path,result)
 payload={"stage":"P12-08_FORWARD_V3_3","contract_id":observation["contract_id"],"acceptance":"DEGRADED_PASS","observation":{"trade_date":observation["trade_date"],"digest":observation["observation_digest"],"row_count":len(observation["rows"]),"path":sealed["path"],"reused":sealed["reused"]},"forward_report":{"path":str(report_path),"status":result["status"],"gate":result["gate"],"observation_digests":result["observation_digests"]},"posterior_outcomes":{"status":"NOT_DUE","horizons":[1,3,5,10],"reason":"POSTERIOR_EVALUATION_NOT_YET_MATERIALIZED"},"historical_replay_excluded_from_forward_count":True,"effect_audit":"OPEN","next_stage":"V3_CALIBRATION_ONLY_AFTER_FORWARD_GATE"}
 out=ROOT/"reports/p12_08/p12_08_stage_gate.json";atomic_write(out,payload);print(json.dumps(payload,ensure_ascii=False,indent=2))
if __name__=="__main__":main()
