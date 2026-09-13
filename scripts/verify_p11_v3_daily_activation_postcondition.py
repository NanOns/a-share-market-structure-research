"""Independently verify the V3 daily activation after its wrapper receipt."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path

import duckdb


ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "database" / "market_research.duckdb"
ENTRY = ROOT / "runtime" / "workbench_entry.json"
PLAN = ROOT / "reports" / "v3" / "daily" / "2026-09-10.plan.json"
BUILD_REPORT = ROOT / "reports" / "v3" / "daily" / "2026-09-10.report.json"
REPORT = ROOT / "reports" / "upgrade_v3" / "P11-V3-DAILY-ACTIVATION-20260913.json"

CONTRACT_VERSION = "V3_P11_DAILY_ACTIVATION_POSTCONDITION_V1_0"
EXPECTED_DOMAINS = ["technical", "strength", "high", "structure", "summary", "member_state"]
PUBLICATION_ID = "m4-8a99c99719061f4f1f166d0b9184506c"


def atomic_write(payload: dict[str, object]) -> None:
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    temporary = REPORT.with_suffix(REPORT.suffix + f".{os.getpid()}.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    os.replace(temporary, REPORT)


def main() -> int:
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    build = json.loads(BUILD_REPORT.read_text(encoding="utf-8"))
    entry = json.loads(ENTRY.read_text(encoding="utf-8"))
    with duckdb.connect(str(DB), read_only=True) as connection:
        binding = connection.execute(
            "SELECT publication_id,domain,snapshot_id FROM publication_analysis_snapshots WHERE publication_id=? AND domain='LOCAL_RECONSTRUCTED'",
            [PUBLICATION_ID],
        ).fetchone()
        snapshot_id = str(build.get("snapshot_binding", {}).get("snapshot_id") or "")
        entry_count = int(connection.execute("SELECT count(*) FROM analysis_snapshot_entries WHERE snapshot_id=?", [snapshot_id]).fetchone()[0]) if snapshot_id else 0
    checks = {
        "v3_primary_entry_remains_active": entry.get("primary_entry", {}).get("route") == "/v3",
        "legacy_fallback_remains_available": entry.get("fallback_entry", {}).get("route") == "/view",
        "plan_is_single_cutoff": plan.get("summary", {}).get("planned_dates") == ["2026-09-10"],
        "plan_status_is_planned": plan.get("status") == "PLANNED" and plan.get("summary", {}).get("task_count") == 104579,
        "build_is_successful": build.get("status") == "BUILT" and build.get("entrypoint") == "V3_DAILY_INCREMENTAL",
        "six_target_domains_are_present": sorted(build.get("target_domains", [])) == sorted(EXPECTED_DOMAINS),
        "execution_is_batched": build.get("executed_object_count") == 6 and build.get("executed_task_count") == 104579,
        "five_domains_are_explicitly_reused": int(build.get("reused_result_objects", 0)) >= 5,
        "technical_rows_calculated": int(build.get("calculated_rows", 0)) == 5932,
        "snapshot_binding_matches_current_publication": bool(binding) and tuple(str(value) for value in binding) == (PUBLICATION_ID, "LOCAL_RECONSTRUCTED", snapshot_id),
        "snapshot_has_entries": entry_count >= 6,
        "build_report_exists": BUILD_REPORT.is_file(),
    }
    status = "FULL_PASS" if all(checks.values()) else "BLOCKED"
    previous = {}
    try:
        previous = json.loads(REPORT.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        pass
    payload = {
        "receipt_id": "P11-V3-DAILY-ACTIVATION-20260913",
        "stage": "P11 V3 daily incremental activation postcondition",
        "status": status,
        "contract_version": CONTRACT_VERSION,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "stage_contract": {
            "spec_section": "§18.7 P04-02；§18.14 P11-04；§20.3–§20.8",
            "scope": "只读复核已提交的 V3 日增量结果、计划、六域执行矩阵和 publication snapshot binding；不重复执行 writer。",
        },
        "checks": checks,
        "publication_id": PUBLICATION_ID,
        "plan_artifact": str(PLAN),
        "build_report_artifact": str(BUILD_REPORT),
        "build_result": {
            "status": build.get("status"),
            "entrypoint": build.get("entrypoint"),
            "plan_id": build.get("plan_id"),
            "planned_task_count": build.get("planned_task_count"),
            "executed_task_count": build.get("executed_task_count"),
            "executed_object_count": build.get("executed_object_count"),
            "calculated_rows": build.get("calculated_rows"),
            "reused_rows": build.get("reused_rows"),
            "reassembled_rows": build.get("reassembled_rows"),
            "reused_result_objects": build.get("reused_result_objects"),
            "identity_rows_added": build.get("identity_rows_added"),
            "db_file_growth_bytes": build.get("db_file_growth_bytes"),
            "source_snapshot_id": build.get("source_snapshot_id"),
            "target_domains": build.get("target_domains"),
            "snapshot_binding": build.get("snapshot_binding"),
        },
        "current_binding": {"publication_id": binding[0], "domain": binding[1], "snapshot_id": binding[2], "entry_count": entry_count} if binding else None,
        "database_boundary": previous.get("database_boundary", {"path": str(DB), "basis": "read-only postcondition"}),
        "initial_wrapper_receipt": {
            "status": previous.get("status"),
            "failed_checks": [key for key, value in (previous.get("checks") or {}).items() if value is False],
            "correction": "外层回执的排序比较与 report_artifact 返回字段判定不代表 writer 事务失败；本回执以已落盘 build report 和当前 DB binding 只读复核为准。",
        },
        "acceptance": "FULL_PASS：V3 日增量已真实完成，technical 批量计算、其它五个域显式复用、快照绑定和落盘回执均通过；逻辑 task 仅覆盖 2026-09-10；未重复执行 writer、未访问或修改 TDX。" if status == "FULL_PASS" else "BLOCKED：V3 日增量后置复核仍有失败项。",
        "known_limits": [
            "本次针对当前已存在的 2026-09-10 publication，不创造新交易日。",
            "P10-03 V3 research signal 效果观察仍由独立 run/episode 门控制，当前仍不宣称效果通过。",
            "旧表继续保留，待 V3 开发和旧页面迁移完成后再逐表复核。",
        ],
        "next_stage": "V3_DAILY_OPERATION_AND_P10_03_EFFECT_OBSERVATION",
        "safety": {
            "writer_reexecuted_by_postcondition": False,
            "tdx_inputs_modified": False,
            "external_online_fetch": False,
            "old_tables_deleted": False,
        },
    }
    atomic_write(payload)
    print(json.dumps({"status": status, "failed_checks": [key for key, value in checks.items() if value is False], "snapshot_id": snapshot_id, "next_stage": payload["next_stage"]}, ensure_ascii=False))
    return 0 if status == "FULL_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
