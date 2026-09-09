from __future__ import annotations

import datetime
import hashlib
import json
import os
import statistics
import sys
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from workbench_service.app import Api, resolve_workbench_path


PHASES = (
    ("M0", "reports/upgrade_m0/M0_RISK_CONVERGENCE_RECEIPT.json", "final_status", "FULL_PASS"),
    ("M1", "reports/upgrade_m1/M1_DATA_FOUNDATION_RECEIPT.json", "final_status", "FULL_PASS"),
    ("M2", "reports/upgrade_m2/M2_SERVICE_READONLY_RECEIPT.json", "final_status", "FULL_PASS"),
    ("M3", "reports/upgrade_m3/M3_AUTOMATIC_INPUT_RECEIPT.json", "final_status", "FULL_PASS"),
    ("M4", "reports/upgrade_m4/M4_ONE_CLICK_PUBLICATION_RECEIPT.json", "final_status", "FULL_PASS"),
    ("M5", "reports/upgrade_m5/M5_OPERATIONS_RECEIPT.json", "final_status", "FULL_PASS"),
)


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def atomic_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    temporary.write_text(value, encoding="utf-8")
    os.replace(temporary, path)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def timed(call, repeats=5):
    cold_started = time.perf_counter()
    value = call()
    cold_ms = (time.perf_counter() - cold_started) * 1000
    samples = []
    for _ in range(repeats):
        started = time.perf_counter()
        value = call()
        samples.append((time.perf_counter() - started) * 1000)
    ordered = sorted(samples)
    p95 = ordered[min(len(ordered) - 1, int(len(ordered) * 0.95))]
    return value, {"cold_ms": round(cold_ms, 3), "hot_samples_ms": [round(x, 3) for x in samples], "hot_median_ms": round(statistics.median(samples), 3), "hot_p95_ms": round(p95, 3)}


def main() -> int:
    start = json.loads((ROOT / "reports/upgrade_m6/M6_START_RECEIPT.json").read_text(encoding="utf-8"))
    chain = {}
    for phase, relative, field, expected in PHASES:
        path = ROOT / relative
        value = json.loads(path.read_text(encoding="utf-8"))
        chain[phase] = {"receipt": relative, "sha256": sha256(path), "status": value.get(field), "pass": value.get(field) == expected}

    m4 = json.loads((ROOT / "reports/upgrade_m4/M4_ONE_CLICK_PUBLICATION_RECEIPT.json").read_text(encoding="utf-8"))
    m5 = json.loads((ROOT / "reports/upgrade_m5/M5_OPERATIONS_RECEIPT.json").read_text(encoding="utf-8"))
    recovery_evidence = {
        "publication": {"receipt": "reports/upgrade_m4/M4_ONE_CLICK_PUBLICATION_RECEIPT.json", "checks": m4.get("checks", {}), "final_status": m4.get("final_status")},
        "operations": {"receipt": "reports/upgrade_m5/M5_OPERATIONS_RECEIPT.json", "checks": m5.get("checks", {}), "restart_failure_rollback_status": m5.get("restart_failure_rollback", {}).get("status"), "final_status": m5.get("final_status")},
    }

    api = Api(ROOT / "data/database/market_research.duckdb")
    publication_by_day = {row["trade_date"]: row["publication_id"] for row in api.publications()["items"]}
    days = []
    performance = {}
    for day in start["acceptance_dates"]:
        publication_id = publication_by_day[day]
        dashboard, dashboard_timing = timed(lambda p=publication_id: api.dashboard(p))
        sectors, sector_timing = timed(lambda p=publication_id: api.sectors(p, "", 1, 50))
        stocks, stock_timing = timed(lambda p=publication_id: api.stocks(p, "", 1, 100))
        queue_evidence = {}
        for queue in ("STEADY", "PULLBACK", "BREAKOUT", "LEADER", "EARLY"):
            listing = api.queues(publication_id, queue, 1, 50)
            sample = listing["items"][0] if listing["items"] else None
            evidence = api.evidence(publication_id, queue, sample["security_id"])["item"] if sample else None
            queue_evidence[queue] = {"total": listing["total"], "page_rows": len(listing["items"]), "sample_security_id": sample.get("security_id") if sample else None, "evidence_available": evidence is not None}
        sector = sectors["items"][0]
        linkage, linkage_timing = timed(lambda p=publication_id, sid=sector["sector_id"]: api.linkage(p, sid, None, 1, 100))
        ranks = [row["sector_member_rank"] for row in linkage["items"]]
        static = resolve_workbench_path(ROOT, day, publication_id)
        shell = static.read_text(encoding="utf-8")
        identity = api.identity(publication_id)
        # Historical imported publications may not carry a render identity in
        # the database.  Never rewrite a sealed publication to hide that fact:
        # bind the exact served shell hash as explicit acceptance evidence.
        static_hash = sha256(static)
        render_evidence = identity.get("render_identity_sha256") or static_hash
        days.append({
            "trade_date": day,
            "publication_id": publication_id,
            "identity": identity,
            "render_identity_evidence": {"sha256": render_evidence, "source": "publication.render_identity_sha256" if identity.get("render_identity_sha256") else "served_static_file_sha256", "legacy_database_value_missing": not bool(identity.get("render_identity_sha256"))},
            "counts": dashboard["counts"],
            "queue_evidence": queue_evidence,
            "linkage": {"sector_id": sector["sector_id"], "sector_name": sector.get("sector_name"), "sector_member_count": linkage["sector_member_count"], "page_rows": len(linkage["items"]), "ranks_nonblank": all(isinstance(x, int) and x > 0 for x in ranks), "ranks_ordered": ranks == sorted(ranks)},
            "thin_api_shell": "const 数据=" not in shell and "/api/queues" in shell and static.stat().st_size < 1_000_000,
            "friendly_evidence_ui": "友好证据" in shell and "这些数值用于解释当前结构" in shell and "href=\"/api/evidence" not in shell,
            "static_path": str(static.relative_to(ROOT)),
            "static_sha256": static_hash,
        })
        performance[day] = {"dashboard": dashboard_timing, "sectors_page_50": sector_timing, "stocks_page_100": stock_timing, "linkage_page_100": linkage_timing}

    all_p95 = [entry["hot_p95_ms"] for day in performance.values() for entry in day.values()]
    checks = {
        "m0_to_m5_receipt_chain": all(item["pass"] for item in chain.values()),
        "two_real_publication_days": len(days) == 2 and len({item["publication_id"] for item in days}) == 2,
        "identity_complete": all(all(item["identity"].get(key) for key in ("source_manifest_sha256", "source_identity_sha256", "computation_identity_sha256", "membership_snapshot_id")) and item["render_identity_evidence"]["sha256"] == item["static_sha256"] for item in days),
        "five_queue_evidence_available": all(len(item["queue_evidence"]) == 5 and all(queue["evidence_available"] or queue["total"] == 0 for queue in item["queue_evidence"].values()) for item in days),
        "linkage_count_and_rank": all(item["linkage"]["sector_member_count"] >= item["linkage"]["page_rows"] and item["linkage"]["ranks_nonblank"] and item["linkage"]["ranks_ordered"] for item in days),
        "thin_api_shell": all(item["thin_api_shell"] for item in days),
        "friendly_evidence_ui": all(item["friendly_evidence_ui"] for item in days),
        "query_p95_under_one_second": max(all_p95, default=0) <= 1000,
        "failure_recovery_evidence": m4.get("final_status") == "FULL_PASS" and m5.get("final_status") == "FULL_PASS" and all(m5.get("checks", {}).values()) and m5.get("restart_failure_rollback", {}).get("status") == "ROLLED_BACK",
    }
    preflight_pass = all(checks.values())
    receipt = {
        "phase": "M6_INDEPENDENT_ACCEPTANCE",
        "contract_version": "m6-independent-acceptance-contract-v1",
        "generated_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "developer_preflight_status": "PASS" if preflight_pass else "BLOCKED",
        "final_status": "AWAITING_EXTERNAL_AUDIT" if preflight_pass else "BLOCKED",
        "checks": checks,
        "receipt_chain": chain,
        "failure_recovery_evidence": recovery_evidence,
        "acceptance_days": days,
        "performance": performance,
        "performance_context": {"mode": "local direct API calls", "cold_calls_recorded_separately": True, "hot_repeats_per_query": 5, "page_size_cap": 100, "target": "hot P95 <= 1000ms", "claim": "measured acceptance evidence only"},
        "identity_warnings": ["Historical publication rows have null render_identity_sha256; M6 binds the exact served static file SHA-256 without mutating sealed database rows."] if any(item["render_identity_evidence"]["legacy_database_value_missing"] for item in days) else [],
        "external_audit": {"status": "NOT_RUN", "auditor": None, "executed_at_utc": None, "blocking_findings": [], "report": None},
        "production_entry_switch_allowed": False,
        "tdx_write_attempted": False,
        "network_data_used": False,
        "next_action": "INDEPENDENT_EXTERNAL_AUDIT" if preflight_pass else "FIX_PREFLIGHT_BLOCKERS",
    }
    receipt["receipt_sha256"] = hashlib.sha256(json.dumps(receipt, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    report = ROOT / "reports/upgrade_m6"
    atomic_json(report / "M6_DEVELOPER_PREFLIGHT_RECEIPT.json", receipt)
    handoff = "\n".join((
        "# M6 独立验收交接",
        "",
        f"- 开发方预检：`{receipt['developer_preflight_status']}`",
        f"- M6 当前状态：`{receipt['final_status']}`",
        "- 验收日期：`" + "`、`".join(start["acceptance_dates"]) + "`",
        "- 最终门禁：独立验收方签发 `EXTERNAL_AUDIT_PASS`。",
        "- 正式入口：在外审通过前不得切换。",
        "",
        "独立验收方应复跑 `pytest -q` 与 `python run_upgrade_m6.py`，实际操作两个日期的队列、证据、分页、板块成员及反向联动，并把执行主体、环境、原始结果和问题清单写入独立报告。开发方预检不得替代该报告。",
        "",
    ))
    atomic_text(report / "M6_EXTERNAL_AUDIT_HANDOFF.md", handoff)
    start.update(status=receipt["final_status"], active_subtask="WAIT_FOR_INDEPENDENT_EXTERNAL_AUDIT" if preflight_pass else "FIX_PREFLIGHT_BLOCKERS", completed_subtasks=[*start.get("completed_subtasks", []), "VERIFY_M0_TO_M5_RECEIPT_CHAIN", "BUILD_TWO_REAL_DAY_DATA_AND_IDENTITY_EVIDENCE", "BUILD_TWO_REAL_DAY_SERVICE_AND_BROWSER_EVIDENCE", "CAPTURE_PERFORMANCE_AND_FAILURE_RECOVERY_EVIDENCE", "PREPARE_EXTERNAL_AUDIT_HANDOFF"])
    start["completed_subtasks"] = list(dict.fromkeys(start["completed_subtasks"]))
    atomic_json(report / "M6_START_RECEIPT.json", start)
    print(json.dumps({"developer_preflight_status": receipt["developer_preflight_status"], "final_status": receipt["final_status"], "receipt_sha256": receipt["receipt_sha256"], "next_action": receipt["next_action"]}, ensure_ascii=False, indent=2))
    return 0 if preflight_pass else 2


if __name__ == "__main__":
    raise SystemExit(main())
