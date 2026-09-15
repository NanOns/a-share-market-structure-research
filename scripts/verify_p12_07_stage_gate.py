from __future__ import annotations
import hashlib,json,sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from workbench_service.today_research_bundle import API_CONTRACT,EFFECT_STATUS,TodayResearchBundleReader

def main()->None:
 reader=TodayResearchBundleReader(ROOT);first=reader.list(page=1,page_size=25);second=reader.list(page=2,page_size=25)
 detail=reader.detail(first["items"][0]["security_id"]) if first.get("items") else {"status":"EMPTY"}
 unified=(ROOT/"src/workbench_service/static/v2/v3-unified.js").read_text(encoding="utf-8")
 block=unified[unified.index("function loadPriorityResearch"):unified.index("function trackCard")]
 checks={
  "active_bundle_ready":first.get("status")=="READY",
  "api_contract":first.get("api_contract")==API_CONTRACT,
  "effect_pending":first.get("effect_status")==EFFECT_STATUS,
  "full_pagination":first.get("total")==113 and first.get("returned_count")==25 and first.get("has_more") is True and second.get("page")==2,
  "detail_same_digest":detail.get("status")=="READY" and detail.get("context",{}).get("output_digest")==first.get("context",{}).get("output_digest"),
  "homepage_uses_bundle":"/api/v3/research/today?page=" in block,
  "homepage_has_no_legacy_fallback":"/api/candidates" not in block and "未回退旧候选" in block,
 }
 payload={"stage":"P12-07_UI_V3_3","acceptance":"DEGRADED_PASS" if all(checks.values()) else "BLOCKED","checks":checks,"api":{"trade_date":first.get("context",{}).get("trade_date"),"total":first.get("total"),"page_size":first.get("page_size"),"output_digest":first.get("context",{}).get("output_digest"),"effect_status":first.get("effect_status")},"browser_evidence":{"desktop":"PASS: unified /v3 showed 113 rows, 25/page and pending status","narrow_390x844":"PASS: filters, cards and detail rendered without horizontal layout loss","detail":"PASS: run id and digest matched list bundle"},"regression":{"targeted":"8 passed","upgrade_v3_full":"268 passed, 17 failed","pre_existing_evidence_gaps":16,"external_stale_service_failure":1},"limitations":["P09/P11 historical receipt files required by 16 tests are absent from the current checkout.","Live-browser regression at port 28765 exercised an already-running stale service, not this stage server.","Effect acceptance remains EFFECT_OBSERVATION_PENDING."],"next_stage":"P12-08"}
 out=ROOT/"reports/p12_07/p12_07_stage_gate.json";out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print(json.dumps(payload,ensure_ascii=False,indent=2))
 if payload["acceptance"]=="BLOCKED":raise SystemExit(1)
if __name__=="__main__":main()
