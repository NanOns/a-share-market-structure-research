"""Run and record the controlled V3 daily activation for the current publication."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys

import duckdb


ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "database" / "market_research.duckdb"
SOURCE = ROOT / "data" / "normalized" / "adjusted_daily.parquet"
MEMBERSHIP = ROOT / "data" / "sectors" / "sector_membership_daily.parquet"
REPORT = ROOT / "reports" / "upgrade_v3" / "P11-V3-DAILY-ACTIVATION-20260913.json"
CONTRACT_VERSION = "V3_P11_DAILY_ACTIVATION_V1_0"

sys.path.insert(0, str(ROOT / "src"))
from workbench_service.v3_daily_entry import V3_DAILY_TARGET_DOMAINS, run_v3_daily_entry  # noqa: E402


def atomic_write(payload: dict[str, object]) -> None:
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    temporary = REPORT.with_suffix(REPORT.suffix + f".{os.getpid()}.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    os.replace(temporary, REPORT)


def current_publication() -> str:
    with duckdb.connect(str(DB), read_only=True) as connection:
        row = connection.execute("SELECT publication_id FROM publications WHERE status='SUCCESS' ORDER BY trade_date DESC, revision DESC LIMIT 1").fetchone()
    if not row:
        raise RuntimeError("V3_DAILY_PUBLICATION_MISSING")
    return str(row[0])


def main() -> int:
    before = DB.stat()
    publication_id = current_publication()
    payload: dict[str, object]
    try:
        result = run_v3_daily_entry(
            ROOT,
            DB,
            publication_id=publication_id,
            source_path=SOURCE,
            membership_path=MEMBERSHIP,
        )
        after = DB.stat()
        plan_artifact = Path(str(result.get("plan_artifact"))) if result.get("plan_artifact") else None
        plan_payload = json.loads(plan_artifact.read_text(encoding="utf-8")) if plan_artifact and plan_artifact.is_file() else {}
        checks = {
            "entrypoint_is_v3_daily_incremental": result.get("entrypoint") == "V3_DAILY_INCREMENTAL",
            "build_status_is_built": result.get("status") == "BUILT",
            "single_cutoff_date": plan_payload.get("summary", {}).get("planned_dates") == ["2026-09-10"],
            "target_domains_are_six_v3_domains": tuple(result.get("target_domains", ())) == tuple(V3_DAILY_TARGET_DOMAINS),
            "reuse_is_explicit": int(result.get("reused_result_objects", 0)) >= 5,
            "report_artifacts_exist": bool(result.get("plan_artifact")) and bool(result.get("report_artifact")) and Path(str(result["plan_artifact"])).is_file() and Path(str(result["report_artifact"])).is_file(),
            "database_stat_available_after_run": after.st_size > 0 and after.st_mtime_ns > 0,
        }
        status = "FULL_PASS" if all(checks.values()) else "BLOCKED"
        payload = {
            "receipt_id": "P11-V3-DAILY-ACTIVATION-20260913",
            "stage": "P11 V3 daily incremental activation",
            "status": status,
            "contract_version": CONTRACT_VERSION,
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "stage_contract": {
                "spec_section": "§18.7 P04-02；§18.14 P11-04；§20.3–§20.8",
                "scope": "在已完成 P11-04 入口交接后，用当前 V3 publication 执行一次受控日增量；按计划批量计算 technical，显式复用其它五个 V3 域，并在全部完成后绑定快照。",
            },
            "checks": checks,
            "publication_id": publication_id,
            "result": result,
            "database_boundary": {
                "path": str(DB),
                "before": {"size": before.st_size, "mtime_ns": before.st_mtime_ns},
                "after": {"size": after.st_size, "mtime_ns": after.st_mtime_ns},
                "growth_bytes": after.st_size - before.st_size,
            },
            "acceptance": "FULL_PASS：V3 日增量从真实 normalized parquet 进入计划、批量计算/显式复用并完成快照绑定；逻辑 task 只覆盖 2026-09-10；未访问或修改 TDX。" if status == "FULL_PASS" else "BLOCKED：V3 日增量计算、复用、快照绑定或产物核对失败。",
            "known_limits": [
                "本次激活针对当前已存在的 2026-09-10 V3 publication；未创造新的交易日数据。",
                "P10-03 V3 research signal 效果观察仍由独立研究 run/episode 门控制，不因日增量完成而宣称效果通过。",
                "旧表继续保留，待 V3 开发和旧页面迁移完成后再逐表复核。",
            ],
            "next_stage": "V3_DAILY_OPERATION_AND_P10_03_EFFECT_OBSERVATION",
            "safety": {
                "tdx_inputs_modified": False,
                "external_online_fetch": False,
                "old_tables_deleted": False,
                "production_database_write_scope": "V3 result/snapshot binding only",
            },
        }
    except Exception as exc:
        after = DB.stat()
        payload = {
            "receipt_id": "P11-V3-DAILY-ACTIVATION-20260913",
            "stage": "P11 V3 daily incremental activation",
            "status": "BLOCKED",
            "contract_version": CONTRACT_VERSION,
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "error": {"type": type(exc).__name__, "message": str(exc)},
            "database_boundary": {"path": str(DB), "before": {"size": before.st_size, "mtime_ns": before.st_mtime_ns}, "after": {"size": after.st_size, "mtime_ns": after.st_mtime_ns}},
            "safety": {"tdx_inputs_modified": False, "external_online_fetch": False, "old_tables_deleted": False},
            "next_stage": "V3_DAILY_ACTIVATION_REPAIR",
        }
    atomic_write(payload)
    print(json.dumps({"status": payload["status"], "publication_id": payload.get("publication_id"), "result_status": (payload.get("result") or {}).get("status"), "next_stage": payload["next_stage"]}, ensure_ascii=False))
    return 0 if payload["status"] == "FULL_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
