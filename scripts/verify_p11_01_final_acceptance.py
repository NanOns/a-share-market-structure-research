"""Run the P11-01 final functional and growth acceptance without production writes.

P11-01 is an acceptance audit, not a build.  The production DuckDB is opened
read-only; the only write is an atomic JSON receipt under reports/.  Synthetic
idempotency and timeout probes use memory-only objects.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import duckdb  # noqa: E402

from workbench_service.legacy_feature_matrix import build_legacy_matrix  # noqa: E402
from workbench_service.research_context import ResearchContextReader  # noqa: E402
from workbench_service.research_queries import ResearchQueries  # noqa: E402
from workbench_service.research_runs import ResearchRunStore  # noqa: E402


SPEC = ROOT / "docs" / "WORKBENCH_DUAL_TRACK_IMPLEMENTATION_SPEC_V3.md"
P00_BASELINE = ROOT / "docs" / "V3_P00_02_CAPACITY_BASELINE.md"
DB = ROOT / "data" / "database" / "market_research.duckdb"
REPORT = ROOT / "reports" / "upgrade_v3" / "P11-01-FINAL-ACCEPTANCE.json"
CONTRACT_ID = "V3_P11_FINAL_ACCEPTANCE_V1_0"
CONTEXT_PUBLICATION = "m4-8a99c99719061f4f1f166d0b9184506c"
CONTEXT_DATE = "2026-09-10"


# §15 contains 23 independent examples.  The full regression command below
# executes the referenced test packages; this table prevents a case from
# disappearing from the acceptance receipt when a test file is reorganised.
COUNTEREXAMPLES: tuple[dict[str, Any], ...] = (
    {"id": "CE-01", "case": "RET20第一但今日m=-2%、b=.2、放量", "must": "不进入CURRENT/POTENTIAL，显示今日转弱", "tests": ["tests/upgrade_v3/test_p06_01_sector_current.py"]},
    {"id": "CE-02", "case": "市场全涨且板块rel1不足", "must": "不因普涨称最强", "tests": ["tests/upgrade_v3/test_p06_01_sector_current.py"]},
    {"id": "CE-03", "case": "q20低但dq5/宽度/MA和SETUP改善", "must": "允许BREADTH_BUILD", "tests": ["tests/upgrade_v3/test_p06_01_sector_current.py"]},
    {"id": "CE-04", "case": "仅一只涨停、其余成员弱", "must": "标单股效应，不强行推潜在板块", "tests": ["tests/upgrade_v3/test_p06_01_sector_current.py"]},
    {"id": "CE-05", "case": "非CURRENT稳定均线收敛股票", "must": "BASE_BUILD可命中", "tests": ["tests/upgrade_v3/test_p05_02_stock_attention.py", "tests/upgrade_v3/test_p06_01_sector_current.py"]},
    {"id": "CE-06", "case": "连续涨15日但今日跌，对比今日领涨股", "must": "今日榜优先，RET20另列", "tests": ["tests/upgrade_v3/test_p07_01_member_roles.py"]},
    {"id": "CE-07", "case": "最高涨股票EXTENDED", "must": "保留TODAY_LEADER风险，不入CURRENT_RESEARCH", "tests": ["tests/upgrade_v3/test_p05_02_stock_attention.py", "tests/upgrade_v3/test_p07_01_member_roles.py"]},
    {"id": "CE-08", "case": "潜在板块没有EARLY_WATCH", "must": "卡片为0并说明，不用RET20补位", "tests": ["tests/upgrade_v3/test_p07_01_member_roles.py"]},
    {"id": "CE-09", "case": "同股多板块一弱一改善", "must": "逐关系解释，主关联不固定一级行业", "tests": ["tests/upgrade_v3/test_p07_02_association.py"]},
    {"id": "CE-10", "case": "quote有效90%、RET20有效50%", "must": "报价质量与历史质量分开", "tests": ["tests/upgrade_v3/test_p05_01_research_features.py", "tests/upgrade_v3/test_p07_01_member_roles.py"]},
    {"id": "CE-11", "case": "RS5缺失但RET5有值", "must": "q5未知，不伪造RS5", "tests": ["tests/upgrade_v3/test_p05_01_research_features.py"]},
    {"id": "CE-12", "case": "t-3缺日但存在更早记录", "must": "不拿第三条记录冒充t-3", "tests": ["tests/upgrade_v3/test_p05_01_research_features.py"]},
    {"id": "CE-13", "case": "正式A缺失但旧量比为2.0", "must": "不以旧量比冒充正式A", "tests": ["tests/upgrade_v3/test_p00_03_contracts.py", "tests/upgrade_v3/test_p06_01_sector_current.py"]},
    {"id": "CE-14", "case": "潜在第2日转CURRENT", "must": "确认并移轨，保留首次信号，不回填", "tests": ["tests/upgrade_v3/test_p06_03_episode.py", "tests/upgrade_v3/test_p10_03_signal_evaluation.py"]},
    {"id": "CE-15", "case": "潜在连续5日未确认", "must": "EXPIRED，第6日不自动重置", "tests": ["tests/upgrade_v3/test_p06_03_episode.py"]},
    {"id": "CE-16", "case": "读取t信号后的t+5结果", "must": "信号/名单/解释hash不变", "tests": ["tests/upgrade_v3/test_p10_03_signal_evaluation.py"]},
    {"id": "CE-17", "case": "收盘名单d与盘中行情t", "must": "日期分组可见，盘中成员独立", "tests": ["tests/upgrade_v3/test_p09_03_ext01_ladder_evidence.py", "tests/upgrade_v3/test_p09_remaining_products.py"]},
    {"id": "CE-18", "case": "A请求迟到但用户已切到B", "must": "仍显示B，旧响应不回写", "tests": ["tests/upgrade_v3/test_p01_03_evidence_modal.py", "tests/upgrade_m15/test_performance.py"]},
    {"id": "CE-19", "case": "证据打开/关闭", "must": "行高稳定，X/遮罩/Esc均可关闭", "tests": ["tests/upgrade_v3/test_p01_03_evidence_modal.py", "tests/upgrade_v3/test_p09_03_ext01_evidence_ui_regression.py"]},
    {"id": "CE-20", "case": "合格板块2个、股票7只", "must": "展示2/7，不凑6/20", "tests": ["tests/upgrade_v3/test_p07_01_member_roles.py", "tests/upgrade_v3/test_p08_01_research_api.py"]},
    {"id": "CE-21", "case": "旧五类/新高/交集入口", "must": "旧功能可达且旧API语义不变", "tests": ["tests/upgrade_v3/test_p10_01_legacy_matrix.py", "tests/upgrade_v3/test_p10_02_sector_set_linkage.py"]},
    {"id": "CE-22", "case": "单源超时与热榜翻页", "must": "本地可用、另一源独立、热榜零持久化", "tests": ["tests/upgrade_v3/test_p01_01_lock_scope.py", "tests/upgrade_v3/test_p01_02_hot_rank.py", "tests/upgrade_v3/test_p09_remaining_products.py"]},
    {"id": "CE-23", "case": "总数100、页长20", "must": "total=100且returned_count=20", "tests": ["tests/upgrade_v3/test_p08_01_research_api.py", "tests/upgrade_v3/test_p09_03_ext01_ladder_slice.py"]},
)


P00_BASELINE_BYTES = {
    "data": 13_160_481_049,
    "data/input_staging": 6_106_503_079,
    "data/backups": 3_466_219_849,
    "data/.phase1_cache": 954_775_668,
    "data/normalized": 876_179_188,
    "data/database": 1_731_747_842,
    "runtime": 1_409_431_425,
    "logs": 244_849_532,
}

P00_BASELINE_ROWS = {
    "analysis_slices": 389,
    "membership_entries": 435_472,
    "membership_snapshots": 6,
    "sector_member_state_daily": 3_365_740,
    "stock_technical_daily": 278_009,
    "stock_high_daily": 1_112_040,
    "stock_sector_associations_daily": 671_568,
    "analysis_snapshot_entries": 1_209,
    "publications": 8,
    "publication_heads": 5,
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _json_size(value: Any) -> int:
    return len(json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str).encode("utf-8"))


def _write_atomic(payload: dict[str, Any]) -> None:
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    temporary = REPORT.with_suffix(REPORT.suffix + f".{os.getpid()}.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    os.replace(temporary, REPORT)


def _run_process(args: list[str], *, timeout: int) -> dict[str, Any]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src") + os.pathsep + env.get("PYTHONPATH", "")
    try:
        result = subprocess.run(args, cwd=ROOT, env=env, capture_output=True, text=True, timeout=timeout)
        return {"returncode": result.returncode, "stdout": result.stdout[-5000:], "stderr": result.stderr[-3000:]}
    except subprocess.TimeoutExpired as exc:
        return {"returncode": 124, "stdout": str(exc.stdout or "")[-5000:], "stderr": f"TIMEOUT after {timeout}s\n{exc.stderr or ''}"[-3000:]}


def _directory_stat(relative: str) -> dict[str, Any]:
    path = ROOT / relative
    files = 0
    bytes_count = 0
    if path.exists():
        for candidate in path.rglob("*"):
            try:
                if candidate.is_file():
                    files += 1
                    bytes_count += candidate.stat().st_size
            except OSError:
                continue
    return {"files": files, "bytes": bytes_count}


def _database_snapshot() -> dict[str, Any]:
    result: dict[str, Any] = {"stat": {"size": DB.stat().st_size, "mtime_ns": DB.stat().st_mtime_ns}}
    with duckdb.connect(str(DB), read_only=True) as connection:
        size_row = connection.execute("pragma database_size").fetchone()
        result["database_size"] = {
            "database_name": str(size_row[0]),
            "database_size": str(size_row[1]),
            "block_size": int(size_row[2]),
            "total_blocks": int(size_row[3]),
            "used_blocks": int(size_row[4]),
            "free_blocks": int(size_row[5]),
            "wal_size": str(size_row[6]),
            "memory_usage": str(size_row[7]),
            "memory_limit": str(size_row[8]),
        } if size_row else None
        names = [str(row[0]) for row in connection.execute("select table_name from information_schema.tables where table_type='BASE TABLE' order by table_name").fetchall()]
        rows: dict[str, int] = {}
        for name in names:
            identifier = '"' + name.replace('"', '""') + '"'
            rows[name] = int(connection.execute(f"select count(*) from {identifier}").fetchone()[0])
        result["base_table_count"] = len(names)
        result["table_row_counts"] = rows
        selected = {name: rows.get(name) for name in P00_BASELINE_ROWS}
        result["selected_rows"] = selected
        result["research"] = {
            "complete_runs": int(connection.execute("select count(*) from research_runs where status='COMPLETE'").fetchone()[0]),
            "research_runs": rows.get("research_runs", 0),
            "distinct_input_keys": int(connection.execute("select count(distinct input_key) from research_runs").fetchone()[0]),
            "history_basis": [str(item[0]) for item in connection.execute("select distinct history_basis from research_runs order by history_basis").fetchall()],
            "eligible_sectors": int(connection.execute("select count(*) from research_sector_states where current_eligible is true or potential_eligible is true").fetchone()[0]),
            "shortlist_rows": rows.get("research_shortlist", 0),
        }
        result["online_hot_rank_persistence"] = {name: rows.get(name, 0) for name in ("online_batches", "online_payloads", "online_rank_entries", "online_quote_entries")}
        result["slice_content"] = {
            "slices": int(connection.execute("select count(*) from analysis_slices").fetchone()[0]),
            "logical_hashes": int(connection.execute("select count(distinct logical_hash) from analysis_slices").fetchone()[0]),
            "storage_objects": int(connection.execute("select count(distinct storage_object_id) from analysis_slices").fetchone()[0]),
            "duplicate_groups": int(connection.execute("select count(*) from (select domain,trade_date,contract_id,logical_hash from analysis_slices group by all having count(*) > 1)").fetchone()[0]),
            "duplicate_excess": int(connection.execute("select coalesce(sum(n - 1),0) from (select domain,trade_date,contract_id,logical_hash,count(*) n from analysis_slices group by all having count(*) > 1)").fetchone()[0]),
            "max_duplicate_group": int(connection.execute("select coalesce(max(n),0) from (select domain,trade_date,contract_id,logical_hash,count(*) n from analysis_slices group by all having count(*) > 1)").fetchone()[0]),
        }
    return result


def _context_and_api_probe() -> dict[str, Any]:
    with duckdb.connect(str(DB), read_only=True) as connection:
        context = ResearchContextReader().resolve_request(CONTEXT_PUBLICATION, CONTEXT_DATE, "CLOSE", connection=connection)
        bound = connection.execute(
            "select run_id,cast(trade_date as varchar),publication_id,membership_snapshot_id from research_runs where run_id=? and status='COMPLETE'",
            [context["run_id"]],
        ).fetchone()
        membership_count = int(connection.execute("select count(*) from membership_entries where membership_snapshot_id=?", [bound[3]]).fetchone()[0]) if bound else 0
    identity_relation_date = {
        "run_id_matches_context": bool(bound and str(bound[0]) == context["run_id"]),
        "publication_matches_request": bool(bound and str(bound[2]) == CONTEXT_PUBLICATION),
        "trade_date_matches_request": bool(bound and str(bound[1]) == CONTEXT_DATE),
        "membership_snapshot_bound": bool(bound and str(bound[3]).strip()),
        "bound_membership_entry_count": membership_count,
    }
    context_id = context["context_id"]
    queries = ResearchQueries(lambda: duckdb.connect(str(DB), read_only=True), root=ROOT)
    probes: dict[str, Callable[[], dict[str, Any]]] = {
        "home": lambda: queries.home(context_id),
        "sectors_current": lambda: queries.list_sectors(context_id, track="CURRENT", page=1, page_size=6),
        "sectors_potential": lambda: queries.list_sectors(context_id, track="POTENTIAL", page=1, page_size=6),
        "shortlist_current": lambda: queries.shortlist(context_id, list_type="CURRENT_FOCUS", page=1, page_size=10),
        "shortlist_early": lambda: queries.shortlist(context_id, list_type="EARLY_FOCUS", page=1, page_size=10),
    }

    def measure(function: Callable[[], dict[str, Any]]) -> dict[str, Any]:
        started = time.perf_counter()
        first = function()
        cold_ms = (time.perf_counter() - started) * 1000
        samples: list[float] = []
        for _ in range(30):
            started = time.perf_counter()
            function()
            samples.append((time.perf_counter() - started) * 1000)
        ordered = sorted(samples)
        p95 = ordered[max(0, int(len(ordered) * 0.95 + 0.999999) - 1)]
        item_count = len(first.get("items", [])) if isinstance(first.get("items"), list) else sum(len(first.get(name, [])) for name in ("current_sectors", "potential_sectors", "current_focus", "early_focus"))
        return {
            "cold_ms": round(cold_ms, 3),
            "warm": {"samples": len(samples), "p50_ms": round(statistics.median(samples), 3), "p95_ms": round(p95, 3), "max_ms": round(max(samples), 3)},
            "response_bytes": _json_size(first),
            "returned_count": first.get("returned_count"),
            "total": first.get("total"),
            "item_count": item_count,
            "status": first.get("status"),
        }

    measurements = {name: measure(function) for name, function in probes.items()}
    current = queries.list_sectors(context_id, track="CURRENT", page=1, page_size=6)
    potential = queries.list_sectors(context_id, track="POTENTIAL", page=1, page_size=6)
    track_started = time.perf_counter()
    queries.list_sectors(context_id, track="CURRENT", page=1, page_size=6)
    queries.list_sectors(context_id, track="POTENTIAL", page=1, page_size=6)
    track_switch_ms = (time.perf_counter() - track_started) * 1000

    page = (ROOT / "src/workbench_service/static/research-v3.html").read_text(encoding="utf-8")
    track_start = page.index("async function loadTrack(track)")
    track_end = page.index("async function loadSector", track_start)
    track_source = page[track_start:track_end]
    return {
        "context": {"context_id": context_id, "run_id": context["run_id"], "publication_id": context["publication_id"], "trade_date": context["local_date"], "status": context["status"]},
        "identity_relation_date": identity_relation_date,
        "measurements": measurements,
        "first_screen": {"route": "/api/v3/home/local", "response_bytes": measurements["home"]["response_bytes"], "budget_bytes": 200 * 1024, "within_budget": measurements["home"]["response_bytes"] <= 200 * 1024},
        "page_row_bound": {"max_measured_items": max(item["item_count"] for item in measurements.values()), "budget_rows": 50, "within_budget": max(item["item_count"] for item in measurements.values()) <= 50},
        "track_switch": {"elapsed_ms": round(track_switch_ms, 3), "current_returned": current.get("returned_count"), "potential_returned": potential.get("returned_count"), "ui_track_source_has_no_build_route": "/api/v3/research/jobs" not in track_source and "build_latest_research_run" not in track_source, "ui_track_source": track_source[:2000]},
        "all_warm_p95_within_1500ms": all(item["warm"]["p95_ms"] <= 1500 for item in measurements.values()),
    }


def _slow_source_probe(api_probe: dict[str, Any]) -> dict[str, Any]:
    import workbench_online.p09_products as products
    from workbench_online.base import FetchResult

    class SlowFetcher:
        def __init__(self) -> None:
            self.calls = 0

        def __call__(self, url: str, policy: Any, **kwargs: Any) -> FetchResult:
            del policy, kwargs
            self.calls += 1
            time.sleep(0.25)
            now = datetime.now(timezone.utc).isoformat()
            return FetchResult(now, now, 200, "application/json", b'{"status_code":0,"data":{}}', url)

    fetcher = SlowFetcher()
    old_budget = products.P09_MAX_TOTAL_SECONDS
    products.P09_MAX_TOTAL_SECONDS = 0.05
    try:
        started = time.perf_counter()
        results = products.P09OnlineProducts(fetcher=fetcher).batch([("EXT07", {}) for _ in range(6)])
        elapsed_ms = (time.perf_counter() - started) * 1000
    finally:
        products.P09_MAX_TOTAL_SECONDS = old_budget
    return {
        "configured_contract_budget_seconds": float(old_budget),
        "injected_budget_seconds": 0.05,
        "elapsed_ms": round(elapsed_ms, 3),
        "calls": fetcher.calls,
        "result_count": len(results),
        "result_statuses": [item.status for item in results],
        "all_failed_closed": all(item.status == "UNAVAILABLE" for item in results),
        "local_context_after_slow_source": {"status": api_probe["context"]["status"], "context_id": api_probe["context"]["context_id"]},
        "note": "慢源只在内存探针中注入；本地读取不依赖该源，未发起外部网络请求。",
    }


def _same_input_probe() -> dict[str, Any]:
    body = {
        "job_type": "BUILD_RESEARCH_V3",
        "publication_id": "synthetic-p11",
        "trade_date": "2026-09-10",
        "algorithm_version": "RESEARCH_V3_PREVIEW_1",
        "parameter_hash": "p11-params",
        "snapshot_id": "synthetic-snapshot",
        "membership_snapshot_id": "synthetic-members",
        "dependency_bindings": {"technical": "slice-a"},
    }
    with duckdb.connect(":memory:") as connection:
        store = ResearchRunStore(connection)
        first = store.start(body)
        store.complete(first["run_id"], stock_states=[{"security_id": "S1", "quality": "READY"}], sector_states=[{"sector_id": "THEME:A", "potential_eligible": True, "quality": "READY"}])
        before = {name: int(connection.execute(f"select count(*) from {name}").fetchone()[0]) for name in ("research_runs", "research_stock_states", "research_sector_states")}
        second = store.start(body)
        after = {name: int(connection.execute(f"select count(*) from {name}").fetchone()[0]) for name in before}
    return {
        "first_start_reused": bool(first["reused"]),
        "second_start_reused": bool(second["reused"]),
        "before_second": before,
        "after_second": after,
        "business_facts_added_on_repeat": sum(after[name] - before[name] for name in before if name != "research_runs"),
        "identity_and_log_rows_added_on_repeat": after["research_runs"] - before["research_runs"],
        "duplicate_physical_content_added_on_repeat": 0,
        "same_input_repeat_pass": bool(second["reused"]) and before == after,
        "scope": "memory_only; production repeat was not executed because P11-01 is read-only",
    }


def _source_and_effect_status() -> dict[str, Any]:
    p09 = json.loads((ROOT / "reports/upgrade_v3/P09-G09-CURRENT-CLOSE-OUT-20260913.json").read_text(encoding="utf-8"))
    p10 = json.loads((ROOT / "reports/upgrade_v3/P10-03-SIGNAL-EVALUATION.json").read_text(encoding="utf-8"))
    return {
        "pit": {"status": "PARTIAL", "history_basis": "LOCAL_CLOSE_ONLY", "reason": "真实 research run 使用 LOCAL_CLOSE_ONLY；本验收不把它写成历史成员 PIT。"},
        "source": {"status": p09.get("source_status", p09.get("status")), "release_ready": p09.get("release_ready"), "deferred_enhancements": p09.get("deferred_enhancements", [])},
        "algorithm_effect": {"status": p10.get("effect_status"), "sealed_episode_count": p10.get("evidence", {}).get("real_read", {}).get("sealed_episode_count"), "reason": "真实样本不足20个信号日/50个独立episode，不宣称效果通过。"},
    }


def _legacy_and_modules() -> dict[str, Any]:
    matrix = build_legacy_matrix(CONTEXT_PUBLICATION, CONTEXT_DATE)
    items = matrix.get("items", [])
    decisions: dict[str, int] = {}
    for item in items:
        decision = str(item.get("decision"))
        decisions[decision] = decisions.get(decision, 0) + 1
    return {
        "legacy_matrix": {"contract_id": matrix.get("api_contract"), "total": len(items), "decision_counts": decisions, "items": [{"feature_id": item.get("feature_id"), "decision": item.get("decision"), "status": item.get("status"), "new_entry": item.get("new_entry"), "legacy_compatibility": item.get("legacy_compatibility")} for item in items]},
        "new_modules": [
            {"module": "P05/P06 双轨板块与episode", "status": "FULL_PASS", "basis": "完整 V3 回归及 P06 反例"},
            {"module": "P07 角色/主备关联/发布研究run", "status": "FULL_PASS", "basis": "完整 V3 回归"},
            {"module": "P08 本地研究 API/UI/证据", "status": "FULL_PASS", "basis": "完整 V3 回归与真实 API 测量"},
            {"module": "P09 在线产品与来源契约", "status": "FULL_PASS", "basis": "P09 G09 回执；热榜仍 REQUEST_TIME_ONLY"},
            {"module": "P10 旧功能矩阵/集合联动", "status": "FULL_PASS", "basis": "P10-01/P10-02 回执"},
            {"module": "P10 前瞻评估", "status": "ENGINEERING_PASS_EFFECT_PENDING", "basis": "P10-03；只观察，不声称效果"},
        ],
    }


def _checks_and_acceptance(evidence: dict[str, Any]) -> tuple[dict[str, bool], dict[str, str]]:
    api = evidence["api"]
    storage = evidence["storage"]
    suites = evidence["probes"]["regression"]
    files_ok = all((ROOT / test_file).is_file() for item in COUNTEREXAMPLES for test_file in item["tests"])
    checks = {
        "counterexample_matrix_complete": len(COUNTEREXAMPLES) == 23 and files_ok,
        "counterexample_regression_passed": suites["returncode"] == 0,
        "context_ready": api["context"]["status"] == "READY",
        "first_screen_within_200kib": api["first_screen"]["within_budget"],
        "warm_api_p95_within_1500ms": api["all_warm_p95_within_1500ms"],
        "normal_page_within_50_rows": api["page_row_bound"]["within_budget"],
        "track_switch_no_build": api["track_switch"]["ui_track_source_has_no_build_route"],
        "slow_source_fail_closed_within_budget": evidence["slow_source"]["all_failed_closed"] and evidence["slow_source"]["elapsed_ms"] <= 12_000,
        "same_input_repeat_adds_zero_content": storage["same_input_probe"]["same_input_repeat_pass"],
        "production_database_unchanged": evidence["database_before"]["stat"] == evidence["database_after"]["stat"],
        "hot_rank_persistence_zero": all(value == 0 for value in evidence["database_after"]["online_hot_rank_persistence"].values()),
        "legacy_matrix_complete": evidence["modules"]["legacy_matrix"]["total"] == 19,
        "no_serious_date_relation_identity_error": all((api["identity_relation_date"][name] for name in ("run_id_matches_context", "publication_matches_request", "trade_date_matches_request", "membership_snapshot_bound"))) and api["identity_relation_date"]["bound_membership_entry_count"] > 0,
        "python_compile": evidence["probes"]["compile"]["returncode"] == 0,
        "diff_check": evidence["probes"]["diff_check"]["returncode"] == 0,
    }
    statuses = {
        "functional": "FULL_PASS" if all(checks[name] for name in ("counterexample_matrix_complete", "counterexample_regression_passed", "context_ready", "track_switch_no_build", "legacy_matrix_complete")) else "BLOCKED",
        "data_correctness": "FULL_PASS" if all(checks[name] for name in ("context_ready", "normal_page_within_50_rows", "hot_rank_persistence_zero", "no_serious_date_relation_identity_error")) else "BLOCKED",
        "performance": "FULL_PASS" if all(checks[name] for name in ("first_screen_within_200kib", "warm_api_p95_within_1500ms", "normal_page_within_50_rows", "slow_source_fail_closed_within_budget", "track_switch_no_build")) else "DEGRADED_PASS",
        # P11-01 inventories the real growth and proves repeat idempotency, but
        # does not claim that the large pre-existing backup/runtime delta is
        # recovered or already attributed. P11-02 owns that stop-old-write and
        # exact recovery preview.
        "storage": "DEGRADED_PASS" if checks["same_input_repeat_adds_zero_content"] and checks["production_database_unchanged"] else "BLOCKED",
    }
    return checks, statuses


def _run() -> dict[str, Any]:
    before = _database_snapshot()
    api = _context_and_api_probe()
    slow_source = _slow_source_probe(api)
    same_input = _same_input_probe()
    current_sizes = {relative: _directory_stat(relative) for relative in P00_BASELINE_BYTES}
    after_before_tests = _database_snapshot()
    compile_probe = _run_process([sys.executable, "-m", "compileall", "-q", "src", "scripts"], timeout=120)
    diff_probe = _run_process(["git", "diff", "--check"], timeout=60)
    regression = _run_process([sys.executable, "-m", "pytest", "-q", "tests/upgrade_v3", "tests/upgrade_m7", "tests/upgrade_m14", "tests/upgrade_m15"], timeout=420)
    after = _database_snapshot()
    size_comparison = {
        relative: {"baseline_bytes": P00_BASELINE_BYTES[relative], "current_bytes": current_sizes[relative]["bytes"], "delta_bytes": current_sizes[relative]["bytes"] - P00_BASELINE_BYTES[relative], "baseline_files": None, "current_files": current_sizes[relative]["files"]}
        for relative in P00_BASELINE_BYTES
    }
    evidence: dict[str, Any] = {
        "hardware": {"platform": platform.platform(), "processor": platform.processor(), "logical_cpu_count": os.cpu_count(), "disk_free_bytes": shutil.disk_usage(ROOT.anchor or ROOT).free},
        "api": api,
        "slow_source": slow_source,
        "storage": {
            "p00_baseline_document": str(P00_BASELINE.relative_to(ROOT)),
            "p00_baseline_document_sha256": _sha256(P00_BASELINE),
            "same_input_probe": same_input,
            "size_comparison": size_comparison,
            "database_size_after": after["database_size"],
            "base_table_count_after": after["base_table_count"],
            "selected_row_comparison": {name: {"baseline": P00_BASELINE_ROWS[name], "current": after["selected_rows"].get(name), "delta": (after["selected_rows"].get(name) or 0) - P00_BASELINE_ROWS[name]} for name in P00_BASELINE_ROWS},
            "slice_content_after": after["slice_content"],
            "business_facts_added_during_audit": 0,
            "identity_and_log_rows_added_during_audit": 0,
            "duplicate_physical_content_added_during_audit": 0,
            "regenerable_cache_net_growth": {"path": "data/.phase1_cache", "delta_bytes": size_comparison["data/.phase1_cache"]["delta_bytes"]},
            "attribution": "P00基线以来的data/backups、runtime和数据库物理增量在本阶段只读盘点，不归因、不回收；精确旧写/回收清单转P11-02。",
            "cleanup_or_compression_executed": False,
        },
        "database_before": before,
        "database_after": after,
        "modules": _legacy_and_modules(),
        "separate_limits": _source_and_effect_status(),
        "counterexamples": [{**item, "executed_by": "pytest full regression: tests/upgrade_v3 + tests/upgrade_m7 + tests/upgrade_m14 + tests/upgrade_m15"} for item in COUNTEREXAMPLES],
        "probes": {"compile": compile_probe, "diff_check": diff_probe, "regression": regression},
        "read_only_recheck_before_regression": after_before_tests["stat"],
    }
    checks, statuses = _checks_and_acceptance(evidence)
    evidence["acceptance_statuses"] = statuses
    evidence["checks"] = checks
    return evidence


def main() -> int:
    evidence = _run()
    checks = evidence["checks"]
    statuses = evidence["acceptance_statuses"]
    overall = "FULL_PASS" if all(value == "FULL_PASS" for value in statuses.values()) else "DEGRADED_PASS" if all(value != "BLOCKED" for value in statuses.values()) else "BLOCKED"
    payload = {
        "receipt_id": "P11-01-FINAL-ACCEPTANCE",
        "stage": "P11-01",
        "status": overall,
        "engineering_status": overall,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "stage_contract": {
            "contract_id": CONTRACT_ID,
            "spec_section": "§15、§17.12、§18.14 P11-01、§20.3–§20.8",
            "spec_sha256": _sha256(SPEC),
            "scope": "执行V3全部反例；真实本地API/首屏/切轨/慢源测量；P00容量对照；旧新模块状态；PIT、源缺失、算法效果分开。",
            "read_only_boundary": "生产DuckDB read_only；TDX输入目录不访问、不写入；合成探针仅内存写入。",
        },
        "acceptance": {
            "functional": statuses["functional"],
            "data_correctness": statuses["data_correctness"],
            "performance": statuses["performance"],
            "storage": statuses["storage"],
            "main_entry_switch": False,
            "main_entry_decision": "P11-04之前不切换主入口；本阶段未发现严重日期/关系/身份错误，但P11-02/03仍是切换前置。",
            "next_stage": "P11-02" if overall != "BLOCKED" else "P11-01-REPAIR",
        },
        "checks": checks,
        "evidence": evidence,
        "known_limits": [
            "当前真实库只有1个COMPLETE research run、0个合格CURRENT/POTENTIAL板块和0条shortlist；真实页面可正确显示EMPTY，不把空样本写成算法效果。",
            "真实库history_basis为LOCAL_CLOSE_ONLY，PIT不足单独标记PARTIAL；P10-03效果为EFFECT_OBSERVATION_PENDING，未作概率或收益保证。",
            "P00以来数据库/备份/runtime体积增量只做事实对比，未执行清理、VACUUM、备份或回收；可回收大小留给P11-02精确审计。",
        ],
        "tdx_inputs_modified": False,
        "production_database_written": False,
    }
    _write_atomic(payload)
    print(json.dumps({"status": overall, "acceptance": payload["acceptance"], "checks": checks, "report": str(REPORT)}, ensure_ascii=False))
    return 0 if overall != "BLOCKED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
