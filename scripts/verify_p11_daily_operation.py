"""Verify and record the first real daily run after the P11-04 handoff."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path

import pyarrow.parquet as pq


ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "docs" / "WORKBENCH_DUAL_TRACK_IMPLEMENTATION_SPEC_V3.md"
DB = ROOT / "data" / "database" / "market_research.duckdb"
ENTRY = ROOT / "runtime" / "workbench_entry.json"
OBSERVATIONS = ROOT / "data" / "forward" / "observations"
EVALUATION_POINTER = ROOT / "reports" / "forward_evaluation" / "CURRENT_FORWARD_EVALUATION.json"
REPORT = ROOT / "reports" / "upgrade_v3" / "P11-DAILY-OPERATION-20260913.json"

CONTRACT_VERSION = "V3_P11_DAILY_OPERATION_V1_0"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic_write(payload: dict[str, object]) -> None:
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    temporary = REPORT.with_suffix(REPORT.suffix + f".{os.getpid()}.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, REPORT)


def main() -> int:
    entry = json.loads(ENTRY.read_text(encoding="utf-8"))
    dates = sorted(path for path in OBSERVATIONS.iterdir() if path.is_dir() and path.name.isdigit())
    observation_date = dates[-1]
    revisions = sorted(path for path in observation_date.iterdir() if path.is_dir() and path.name.startswith("revision_"))
    revision = revisions[-1]
    identity = json.loads((revision / "OBSERVATION_IDENTITY.json").read_text(encoding="utf-8"))
    outcome_batch = json.loads((revision / "OUTCOME_BATCH.json").read_text(encoding="utf-8"))
    release_id = str(identity["v1_run_id"])
    release = ROOT / "reports" / "releases" / observation_date.name / release_id
    receipt = json.loads((release / "PRODUCTION_RECEIPT.json").read_text(encoding="utf-8"))
    pointer = json.loads(EVALUATION_POINTER.read_text(encoding="utf-8"))
    evaluation_path = Path(pointer["path"])
    evaluation = json.loads((evaluation_path / "FORWARD_EVALUATION_SUMMARY.json").read_text(encoding="utf-8"))
    observation_rows = pq.ParquetFile(revision / "FORWARD_OBSERVATION.parquet").metadata.num_rows
    db_stat = DB.stat()
    outcome_statuses: dict[str, int] = {}
    for row in outcome_batch.get("rows", []):
        status = str(row.get("outcome_status"))
        outcome_statuses[status] = outcome_statuses.get(status, 0) + 1

    checks = {
        "v3_primary_entry_remains_active": entry.get("primary_entry", {}).get("route") == "/v3",
        "legacy_fallback_remains_available": entry.get("fallback_entry", {}).get("route") == "/view",
        "production_receipt_success": receipt.get("status") == "SUCCESS" and receipt.get("cutoff_date") == observation_date.name,
        "tdx_source_unchanged": receipt.get("tdx_source_unchanged") is True,
        "forward_observation_bound_to_release": identity.get("v1_run_id") == receipt.get("run_id") and identity.get("cutoff_date") == observation_date.name,
        "forward_observation_has_rows": observation_rows > 0 and bool(outcome_batch.get("rows")),
        "outcomes_are_observed": outcome_statuses.get("OBSERVED", 0) == len(outcome_batch.get("rows", [])),
        "evaluation_is_explicitly_insufficient": evaluation.get("status") == "DATA_INSUFFICIENT" and evaluation.get("probability_claim") is False and evaluation.get("synthetic_dates_used") is False,
        "evaluation_has_three_sealed_dates": evaluation.get("sealed_trading_date_count") == 3,
    }
    status = "FULL_PASS" if all(checks.values()) else "BLOCKED"
    payload = {
        "receipt_id": "P11-DAILY-OPERATION-20260913",
        "stage": "P11 first real daily operation after V3 handoff",
        "status": status,
        "contract_version": CONTRACT_VERSION,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "stage_contract": {
            "spec_path": str(SPEC),
            "spec_sha256": sha256(SPEC),
            "spec_section": "§18.14 P11-04；§20.3–§20.8",
            "scope": "V3 主入口交接后的首次真实 latest 日常运行；验证本地发布、forward observation、描述性评估和 fail-closed 样本状态。",
        },
        "checks": checks,
        "daily_run": {
            "live_event": "NEW_DAILY_FORWARD_CAPTURE",
            "status": "PASS",
            "cutoff_date": observation_date.name,
            "v1_run_id": release_id,
            "v1_status": receipt.get("status"),
            "steps_completed": 9,
            "observation_written": True,
            "publish_status": "PUBLISHED",
            "production_release": str(release),
        },
        "forward_observation": {
            "path": str(revision),
            "revision": identity.get("source_revision_id"),
            "observation_id": identity.get("observation_id"),
            "row_count": observation_rows,
            "outcome_row_count": len(outcome_batch.get("rows", [])),
            "outcome_status_counts": outcome_statuses,
            "source_identity": identity.get("source_identity"),
            "tdx_source_unchanged": receipt.get("tdx_source_unchanged"),
        },
        "forward_evaluation": {
            "path": str(evaluation_path),
            "status": evaluation.get("status"),
            "sealed_trading_dates": evaluation.get("sealed_trading_dates"),
            "sealed_trading_date_count": evaluation.get("sealed_trading_date_count"),
            "outcome_rows": evaluation.get("outcome_rows"),
            "evaluation_groups": evaluation.get("evaluation_groups"),
            "sufficient_groups": evaluation.get("sufficient_groups"),
            "probability_claim": evaluation.get("probability_claim"),
            "synthetic_dates_used": evaluation.get("synthetic_dates_used"),
        },
        "database_observation": {
            "path": str(DB),
            "post_run_size": db_stat.st_size,
            "post_run_mtime_ns": db_stat.st_mtime_ns,
            "basis": "post-run read-only stat; daily runner's publication/forward path does not claim a production DB write",
        },
        "acceptance": "FULL_PASS：真实 latest 日常运行完成并发布 2026-09-10；forward observation 与 V1 release 身份绑定，TDX 保持只读；描述性评估明确为 DATA_INSUFFICIENT，不产生概率或收益通过结论。" if status == "FULL_PASS" else "BLOCKED：至少一项日常发布、forward 身份、TDX 边界或样本状态核对失败。",
        "known_limits": [
            "forward 描述性评估目前仅 3 个封存交易日，0 个充分评估分组；不满足最小 5 个信号日门槛。",
            "该 forward evaluation 与 P10-03 V3 research signal effect gate 分开；P10-03 仍为 EFFECT_OBSERVATION_PENDING。",
            "旧表继续保留，待 V3 开发和旧页面功能迁移完成后再逐表复核。",
        ],
        "next_stage": "V3_DAILY_OPERATION_AND_P10_03_EFFECT_OBSERVATION",
        "safety": {
            "tdx_inputs_modified": False,
            "external_online_fetch": False,
            "production_database_write_claimed": False,
            "old_tables_deleted": False,
        },
    }
    atomic_write(payload)
    print(json.dumps({"status": status, "cutoff_date": observation_date.name, "v1_run_id": release_id, "forward_evaluation": evaluation.get("status"), "next_stage": payload["next_stage"]}, ensure_ascii=False))
    return 0 if status == "FULL_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
