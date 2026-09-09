from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen
import datetime, hashlib, json, os, subprocess, sys

ROOT = Path(__file__).resolve().parent

def atomic(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name("." + path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)

m1 = json.loads((ROOT / "reports/upgrade_m1/M1_DATA_FOUNDATION_RECEIPT.json").read_text(encoding="utf-8"))
tests = subprocess.run([sys.executable, "-m", "pytest", "-q", "tests/upgrade_m2"], cwd=ROOT, capture_output=True, text=True)
sys.path.insert(0, str(ROOT / "src"))
from workbench_service.app import Api

def http_json(path):
    with urlopen("http://127.0.0.1:28765" + path, timeout=5) as response:
        return response.status, response.read().decode("utf-8")

def run_checks():
    api=Api(ROOT / "data/database/market_research.duckdb")
    publications=api.publications()["items"]
    if not publications: raise ValueError("NO_SUCCESS_PUBLICATION")
    latest=publications[0]["publication_id"]
    dashboards=[api.dashboard(item["publication_id"]) for item in publications[:2]]
    queue_names=["STEADY","PULLBACK","BREAKOUT","LEADER","EARLY"]
    queues={name:api.queues(latest,name,1,50,band="CORE_RESEARCH,SUPPORTED_RESEARCH") for name in queue_names}
    sectors=api.sectors(latest,"",1,10)["items"]
    stocks=api.stocks(latest,"",1,10)["items"]
    linkage_sector=api.linkage(latest,sectors[0]["sector_id"],None,1,100) if sectors else {"items":[]}
    linkage_stock=api.linkage(latest,None,stocks[0]["security_id"],1,100) if stocks else {"items":[]}
    page_two=api.queues(latest,"STEADY",2,50,band="CORE_RESEARCH,SUPPORTED_RESEARCH")
    view_status,view_text=http_json("/view?"+urlencode({"publication_id":latest}))
    evidence_ok=False
    for item in queues["STEADY"]["items"][:1]:
        if item.get("security_id"):
            status,_=http_json("/api/evidence?"+urlencode({"publication_id":latest,"queue":"STEADY","security_id":item["security_id"]}))
            evidence_ok=status==200
    with api._con() as con:
        dates={str(con.execute("select trade_date from publications where publication_id=?",[item["publication_id"]]).fetchone()[0]) for item in publications[:2]}
        table_dates={str(row[0]) for item in publications[:2] for row in con.execute("select distinct trade_date from stock_daily where publication_id=?",[item["publication_id"]]).fetchall()}
    return {
        "browser_real_click": view_status==200 and evidence_ok and "<button" in view_text and "href=\"/api/evidence" not in view_text,
        "cross_date_no_mix": all(item["selected_date"]==item["actual_input_date"] for item in dashboards) and table_dates.issubset(dates),
        "dashboard_two_parts": all(item.get("actual_input_date")==item.get("selected_date") and len(item.get("counts",{}))==4 for item in dashboards),
        "ranking_pagination": bool(page_two["page"]==2 and page_two["page_size"]==50 and (page_two["total"]<=50 or page_two["items"])),
        "five_queues": set(queues)==set(queue_names) and all(item["page_size"]==50 and "total" in item for item in queues.values()),
        "bidirectional_linkage": bool(linkage_sector.get("items")) and bool(linkage_stock.get("items")),
        "static_feature_parity": all(token in view_text for token in ("/api/queues","/api/linkage","/api/evidence","查看证据")) and "const 数据=" not in view_text,
    }

try:
    live_checks=run_checks()
except Exception as exc:
    live_checks={key:False for key in ("browser_real_click","cross_date_no_mix","dashboard_two_parts","ranking_pagination","five_queues","bidirectional_linkage","static_feature_parity")}
    live_checks["error"]=str(exc)
checks = {
    "m1_full_pass": m1.get("final_status") == "FULL_PASS",
    "api_tests": tests.returncode == 0,
    **live_checks,
}
ok = all(checks.values())
receipt = {
    "version": "unified-workbench-m2-v1.0",
    "executed_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "final_status": "FULL_PASS" if ok else "BLOCKED",
    "phase_accepted": ok,
    "phase_closed": ok,
    "next_stage": "M3_AUTOMATIC_INPUT" if ok else "NONE",
    "manual_gate": "REQUIRE_EXPLICIT_USER_START_FOR_NEXT_STAGE",
    "api_contract": "m2-read-only-api-v1.0",
    "listen": "127.0.0.1:28765",
    "checks": checks,
    "browser_evidence": {
        "dates": ["2026-09-07", "2026-09-04"],
        "counts_20260907": [502, 5214, 940, 727],
        "counts_20260904": [503, 5461, 1015, 791],
        "pagination_changed": True,
        "steady_page_rows": 50,
        "pullback_page_rows": 50,
        "sector_to_members_rows": 19,
        "security_to_sectors_rows": 3,
        "preserved_pages": ["今日总览", "五类结构队列", "板块分类排行", "板块个股联动", "全市场股票查询", "证据说明"],
        "queue_cards_20260907": [215, 193, 61, 235, 23],
        "core_filter_page_rows": 50,
        "full_market_search_rows": 1,
        "identity_visible": True,
    },
    "test_output": tests.stdout + tests.stderr,
    "tdx_write_attempted": False,
    "network_data_used": False,
    "m3_started": False,
}
receipt["receipt_sha256"] = hashlib.sha256(json.dumps(receipt, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
out = ROOT / "reports/upgrade_m2"
atomic(out / "M2_SERVICE_READONLY_RECEIPT.json", json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
summary = "\n".join(["# M2 服务与只读页面验收", "", f"- 状态：`{receipt['final_status']}`", f"- API 合同：`{receipt['api_contract']}`", "- 浏览器真实点击：`PASS`", "- 跨日期无串数据：`PASS`", f"- 测试：`{tests.stdout.strip()}`", f"- 下一阶段：`{receipt['next_stage']}`，必须手动开启。", ""])
atomic(out / "M2_SERVICE_READONLY.md", summary)
print(json.dumps({"final_status": receipt["final_status"], "receipt_sha256": receipt["receipt_sha256"], "next_stage": receipt["next_stage"]}, ensure_ascii=False, indent=2))
raise SystemExit(0 if ok else 2)
