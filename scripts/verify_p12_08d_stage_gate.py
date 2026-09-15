from __future__ import annotations
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"src"))
from workbench_analysis.forward_v3_3 import CONTRACT_ID,atomic_write

def main():
 report=json.loads((ROOT/"reports/p12_08/forward_report.json").read_text(encoding="utf-8"));dimensions=report["reporting_dimensions"]
 checks={"current_contract":report["contract_id"]==CONTRACT_ID,"liquidity_complete":dimensions["liquidity"]["available"]==113 and dimensions["liquidity"]["missing"]==0,"relations_complete":dimensions["industry_relation_coverage"]["available"]==113 and dimensions["theme_relation_coverage"]["available"]==113,"missing_dimensions_explicit":dimensions["market_strength"]["status"]==dimensions["volatility"]["status"]=="UNAVAILABLE","effect_still_pending":report["status"]=="EFFECT_OBSERVATION_PENDING"}
 payload={"stage":"P12-08D_REPORTING_DIMENSIONS","contract_id":CONTRACT_ID,"acceptance":"DEGRADED_PASS" if all(checks.values()) else "BLOCKED","checks":checks,"reporting_dimensions":dimensions,"limitations":["ACTIVE_BUNDLE_HAS_NO_MARKET_STRENGTH","ACTIVE_BUNDLE_HAS_NO_VOLATILITY"],"next_stage":"NEXT_REAL_CLOSE_OBSERVATION"}
 atomic_write(ROOT/"reports/p12_08/p12_08d_stage_gate.json",payload);print(json.dumps(payload,ensure_ascii=False,indent=2))
if __name__=="__main__":main()
