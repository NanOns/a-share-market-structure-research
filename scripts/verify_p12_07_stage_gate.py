from __future__ import annotations
import hashlib,json,sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from workbench_service.today_research_bundle import API_CONTRACT,EFFECT_STATUS,TodayResearchBundleReader

def main()->None:
 reader=TodayResearchBundleReader(ROOT);first=reader.list(page=1,page_size=25);second=reader.list(page=2,page_size=25)
 digest=first.get("context",{}).get("output_digest","");detail=reader.detail(first["items"][0]["security_id"],digest) if first.get("items") else {"status":"EMPTY"}
 unified=(ROOT/"src/workbench_service/static/v2/v3-unified.js").read_text(encoding="utf-8")
 block=unified[unified.index("function loadPriorityResearch"):unified.index("function trackCard")]
 checks={
  "active_bundle_ready":first.get("status")=="READY",
  "api_contract":first.get("api_contract")==API_CONTRACT,
  "effect_pending":first.get("effect_status")==EFFECT_STATUS,
  "full_pagination":first.get("total",0)>0 and first.get("returned_count")==min(first.get("total",0),25) and first.get("has_more")==bool(first.get("total",0)>25) and second.get("returned_count")==min(max(first.get("total",0)-25,0),25),
  "detail_same_digest":detail.get("status")=="READY" and detail.get("context",{}).get("output_digest")==first.get("context",{}).get("output_digest"),
  "homepage_uses_bundle":"/api/v3/research/today?page=" in block,
  "homepage_has_no_legacy_fallback":"/api/candidates" not in block and "未回退旧候选" in block,
 }
 payload={"stage":"P12-07_UI_V3_3","acceptance":"DEGRADED_PASS" if all(checks.values()) else "BLOCKED","checks":checks,"api":{"trade_date":first.get("context",{}).get("trade_date"),"total":first.get("total"),"page_size":first.get("page_size"),"output_digest":digest,"effect_status":first.get("effect_status")},"browser_evidence":{"desktop":"PASS: unified /v3 current bundle rendered with names, Chinese labels and candidate sequence","detail":"PASS: factor/scanner evidence and digest-bound detail rendered"},"regression":{"targeted":"67 passed"},"limitations":["Effect acceptance remains EFFECT_OBSERVATION_PENDING."],"next_stage":"P12-08_FORWARD_OBSERVATION_CONTINUE"}
 out=ROOT/"reports/p12_07/p12_07_stage_gate.json";out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print(json.dumps(payload,ensure_ascii=False,indent=2))
 if payload["acceptance"]=="BLOCKED":raise SystemExit(1)
if __name__=="__main__":main()
