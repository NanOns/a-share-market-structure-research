from __future__ import annotations
import json,sys
from pathlib import Path
import duckdb
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"src"))
from workbench_analysis.forward_outcome_v3_3 import CONTRACT_ID,plan_outcomes,seal_plan
from workbench_analysis.forward_v3_3 import CONTRACT_ID as OBSERVATION_CONTRACT,atomic_write

def main():
 observations=[]
 for path in sorted((ROOT/"data/forward_v3_3/observations").glob("*/*.json")):
  value=json.loads(path.read_text(encoding="utf-8"))
  if value.get("contract_id")==OBSERVATION_CONTRACT:observations.append(value)
 if not observations:raise SystemExit("NO_FORWARD_OBSERVATIONS")
 parquet=ROOT/"data/normalized/adjusted_daily.parquet"
 with duckdb.connect(database=":memory:") as connection:sessions=[row[0] for row in connection.execute("select distinct date from read_parquet(?) order by date",[str(parquet)]).fetchall()]
 as_of=max(sessions);plan=plan_outcomes(observations,sessions,as_of);plan_path=ROOT/"reports/p12_08/outcome_plan.json";seal_plan(plan_path,plan)
 receipt={"stage":"P12-08B_FORWARD_OUTCOME_PLAN","contract_id":CONTRACT_ID,"acceptance":"DEGRADED_PASS","plan_path":str(plan_path),"plan_digest":plan["plan_digest"],"as_of_data_date":str(as_of),"episode_count":plan["episode_count"],"outcome_rows":len(plan["rows"]),"summary":plan["summary"],"returns_materialized":False,"tdx_modified":False,"effect_status":"EFFECT_OBSERVATION_PENDING","next_stage":"NEXT_REAL_CLOSE_OBSERVATION"}
 atomic_write(ROOT/"reports/p12_08/p12_08b_stage_gate.json",receipt);print(json.dumps(receipt,ensure_ascii=False,indent=2))
if __name__=="__main__":main()
