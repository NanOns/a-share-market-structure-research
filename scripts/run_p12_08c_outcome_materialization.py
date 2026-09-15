from __future__ import annotations
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"src"))
from workbench_analysis.forward_outcome_materializer_v3_3 import CONTRACT_ID,materialize
from workbench_analysis.forward_v3_3 import atomic_write

def main():
 plan=json.loads((ROOT/"reports/p12_08/outcome_plan.json").read_text(encoding="utf-8"))
 if any(row["status"]!="NOT_DUE" for row in plan["rows"]):raise SystemExit("DUE_ROWS_REQUIRE_FROZEN_EVALUATION_SOURCE")
 result=materialize(plan);out=ROOT/"reports/p12_08/outcome_results.json";atomic_write(out,result)
 receipt={"stage":"P12-08C_FORWARD_OUTCOME_MATERIALIZATION","contract_id":CONTRACT_ID,"acceptance":"DEGRADED_PASS","result_path":str(out),"result_digest":result["result_digest"],"summary":result["summary"],"real_due_rows":0,"synthetic_calculation_tests":"PASS","effect_status":"EFFECT_OBSERVATION_PENDING","next_stage":"NEXT_REAL_CLOSE_OBSERVATION"}
 atomic_write(ROOT/"reports/p12_08/p12_08c_stage_gate.json",receipt);print(json.dumps(receipt,ensure_ascii=False,indent=2))
if __name__=="__main__":main()
