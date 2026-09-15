import json
import threading
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

from workbench_service import app
from workbench_service.research_bundle_v3_3 import activate_bundle, build_bundle
from workbench_service.today_research_bundle import TodayResearchBundleReader

ROOT = Path(__file__).resolve().parents[2]

def identity():
 return {"publication_id":"pub","snapshot_id":"snap","membership_snapshot_id":"members","research_run_id":"run","parameter_hash":"params","dependency_lock_hash":"deps","trade_date":"2026-09-14"}

def rows():
 return [
  {"security_id":"SH.600001","matched_categories":["LAUNCH_CONFIRM"],"primary_category":"LAUNCH_CONFIRM","selection_mode":"SUPPORTED","rank_status":"QUALIFIED_UNRANKED"},
  {"security_id":"SZ.000002","matched_categories":["TREND_CONTINUE"],"primary_category":"TREND_CONTINUE","selection_mode":"INDEPENDENT","rank_status":"SCORED","category_rank":1,"category_score":80.0},
 ]

def reader(tmp_path):
 built=build_bundle(tmp_path/"bundles",identity(),rows(),{"factor":"v1"});pointer=tmp_path/"current.json";activate_bundle(Path(built["path"]),pointer);return TodayResearchBundleReader(tmp_path,pointer)

def test_list_filter_pagination_and_detail_share_verified_identity(tmp_path):
 service=reader(tmp_path)
 first=service.list(page=1,page_size=1)
 assert first["status"]=="READY" and first["total"]==2 and first["has_more"] is True
 assert first["context"]["research_run_id"]=="run" and first["effect_status"]=="EFFECT_OBSERVATION_PENDING"
 filtered=service.list(category="TREND_CONTINUE",selection_mode="INDEPENDENT",q="000002")
 assert [item["security_id"] for item in filtered["items"]]==["SZ.000002"]
 detail=service.detail("sz.000002")
 assert detail["status"]=="READY" and detail["context"]["output_digest"]==filtered["context"]["output_digest"]

def test_missing_and_tampered_bundle_fail_closed_without_results(tmp_path):
 missing=TodayResearchBundleReader(tmp_path,tmp_path/"missing.json").list()
 assert missing["status"]=="NOT_BUILT" and missing["items"]==[]
 service=reader(tmp_path);active=json.loads(service.pointer.read_text(encoding="utf-8"));results=Path(active["bundle_path"])/"results.json";results.write_text("[]\n",encoding="utf-8")
 failed=service.list()
 assert failed["status"]=="UNAVAILABLE" and failed["items"]==[] and "HASH_MISMATCH" in failed["code"]

def test_detail_is_bound_to_the_list_bundle_digest(tmp_path):
 service=reader(tmp_path);listing=service.list()
 assert service.detail("SZ.000002",listing["context"]["output_digest"])["status"]=="READY"
 changed=service.detail("SZ.000002","wrong-digest")
 assert changed["status"]=="UNAVAILABLE"
 assert changed["empty_state"]["code"]=="BUNDLE_CONTEXT_CHANGED"

def test_http_routes_and_static_page_use_new_bundle_without_legacy_candidate_fallback(tmp_path):
 from workbench_db import WorkbenchRepository
 database=tmp_path/"api.duckdb"
 with WorkbenchRepository(ROOT,database):pass
 server=ThreadingHTTPServer(("127.0.0.1",0),app.make_handler(ROOT,database));thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
 try:
  base=f"http://127.0.0.1:{server.server_port}"
  listing=json.load(urllib.request.urlopen(base+"/api/v3/research/today?page=1&page_size=5"))
  detail=json.load(urllib.request.urlopen(base+"/api/v3/research/today/"+listing["items"][0]["security_id"]))
  html=urllib.request.urlopen(base+"/v3").read().decode("utf-8")
  script=urllib.request.urlopen(base+"/v2/v3-unified.js").read().decode("utf-8")
  assert listing["status"]=="READY" and listing["returned_count"]==5
  assert detail["context"]["output_digest"]==listing["context"]["output_digest"]
  assert "今日 V3.3 算法候选" in html
  assert "/api/v3/research/today" in script and "未回退旧候选" in script
  priority=script[script.index("function loadPriorityResearch"):script.index("function trackCard")]
  assert "/api/candidates" not in priority
 finally:server.shutdown();server.server_close();thread.join()

def test_page_has_narrow_layout_filters_pagination_and_detail():
 html=(ROOT/"src/workbench_service/static/research-v3.html").read_text(encoding="utf-8")
 for marker in ('@media(max-width:560px)','today-category','today-mode','today-prev','today-next','today-modal'):
  assert marker in html
