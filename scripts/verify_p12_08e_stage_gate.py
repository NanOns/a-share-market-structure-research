from __future__ import annotations
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"src"))
from workbench_analysis.forward_v3_3 import atomic_write
from workbench_service.research_bundle_v3_3 import read_active
def main():
 path=ROOT/"reports/p12_08/p12_08e_stage_gate.json";receipt=json.loads(path.read_text(encoding="utf-8"));active=read_active(ROOT/"data/current/ACTIVE_RESEARCH_BUNDLE_V3_3.json");report=json.loads((ROOT/"reports/p12_08/forward_report.json").read_text(encoding="utf-8"));dimensions=report["reporting_dimensions"]
 population=sum(report['scenario_counts'].values())
 checks={"active_bundle_v2":active["contract_id"]=="TODAY_RESEARCH_BUNDLE_V3_3_CANDIDATE_02","pointer_verified":active["output_digest"]==receipt["bundle"]["output_digest"],"market_strength_complete":dimensions["market_strength"]["available"]==population and dimensions["market_strength"]["missing"]==0,"volatility_complete":dimensions["volatility"]["available"]==population and dimensions["volatility"]["missing"]==0,"real_signal_days_present":report["gate"]["signal_days"]>=1,"effect_pending":report["status"]=="EFFECT_OBSERVATION_PENDING"}
 receipt.update({"acceptance":"DEGRADED_PASS" if all(checks.values()) else "BLOCKED","checks":checks,"forward_observation_digest":report["observation_digests"][-1],"next_stage":"NEXT_REAL_CLOSE_OBSERVATION"});atomic_write(path,receipt);print(json.dumps(receipt,ensure_ascii=False,indent=2))
if __name__=="__main__":main()
