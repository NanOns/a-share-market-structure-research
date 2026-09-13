"""Record the first read-only daily preflight after the P11-04 handoff."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "docs" / "WORKBENCH_DUAL_TRACK_IMPLEMENTATION_SPEC_V3.md"
DB = ROOT / "data" / "database" / "market_research.duckdb"
ENTRY = ROOT / "runtime" / "workbench_entry.json"
LOCK = ROOT / "runtime" / "locks" / "daily_production.lock"
P10_REPORT = ROOT / "reports" / "upgrade_v3" / "P10-03-SIGNAL-EVALUATION.json"
REPORT = ROOT / "reports" / "upgrade_v3" / "P11-POST-HANDOFF-DAILY-PREFLIGHT-20260913.json"

CONTRACT_VERSION = "V3_P11_POST_HANDOFF_DAILY_PREFLIGHT_V1_0"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic_write(payload: dict[str, object]) -> None:
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    temporary = REPORT.with_suffix(REPORT.suffix + f".{os.getpid()}.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, REPORT)


def main() -> int:
    before = DB.stat()
    process = subprocess.run(
        [sys.executable, str(ROOT / "run_daily.py"), "--date", "latest", "--dry-run"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=180,
    )
    after = DB.stat()
    try:
        daily = json.loads(process.stdout)
    except json.JSONDecodeError:
        daily = {"status": "INVALID_DRY_RUN_OUTPUT", "stdout_tail": process.stdout[-2000:]}

    entry = json.loads(ENTRY.read_text(encoding="utf-8"))
    p10 = json.loads(P10_REPORT.read_text(encoding="utf-8"))
    checks = {
        "current_primary_route_is_v3": entry.get("primary_entry", {}).get("route") == "/v3",
        "legacy_fallback_is_preserved": entry.get("fallback_entry", {}).get("route") == "/view",
        "daily_dry_run_ready": process.returncode == 0 and daily.get("status") == "DRY_RUN_READY",
        "cutoff_is_local_and_normal": daily.get("cutoff_status") == "NORMAL_NEW_TRADING_DAY" and daily.get("resolved_cutoff_date") == daily.get("local_tdx_latest_session"),
        "database_unchanged": before.st_size == after.st_size and before.st_mtime_ns == after.st_mtime_ns,
        "daily_lock_released": not LOCK.exists(),
        "p10_effect_status_remains_pending_or_observed": p10.get("effect_status") in {"EFFECT_OBSERVATION_PENDING", "EFFECT_OBSERVED"},
    }
    status = "FULL_PASS" if all(checks.values()) else "BLOCKED"
    payload = {
        "receipt_id": "P11-POST-HANDOFF-DAILY-PREFLIGHT-20260913",
        "stage": "P11 post-handoff daily preflight",
        "status": status,
        "contract_version": CONTRACT_VERSION,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "stage_contract": {
            "spec_path": str(SPEC),
            "spec_sha256": sha256(SPEC),
            "spec_section": "§18.14 P11-04；§20.3–§20.8",
            "scope": "主入口交接后的首次只读日常输入预检；不发布新生产 run，不写生产数据库，不执行在线采集。",
        },
        "checks": checks,
        "daily_dry_run": {
            "returncode": process.returncode,
            "status": daily.get("status"),
            "run_id": daily.get("run_id"),
            "system_date": daily.get("system_date"),
            "master_calendar_latest_session": daily.get("master_calendar_latest_session"),
            "local_tdx_latest_session": daily.get("local_tdx_latest_session"),
            "resolved_cutoff_date": daily.get("resolved_cutoff_date"),
            "cutoff_status": daily.get("cutoff_status"),
            "file_count": (daily.get("evidence_summary") or {}).get("file_count"),
            "readiness_file_count": daily.get("readiness_file_count"),
        },
        "database_boundary": {
            "path": str(DB),
            "before": {"size": before.st_size, "mtime_ns": before.st_mtime_ns},
            "after": {"size": after.st_size, "mtime_ns": after.st_mtime_ns},
        },
        "p10_03": {
            "engineering_status": p10.get("engineering_status"),
            "effect_status": p10.get("effect_status"),
            "real_read": p10.get("evidence", {}).get("real_read", {}),
        },
        "acceptance": "FULL_PASS：P11-04 后默认入口仍为 V3，/view 回退仍保留；dry-run 返回 DRY_RUN_READY、截止日与本地 TDX 最新交易日一致，生产库未变且锁已释放。该回执不等于真实生产发布。" if status == "FULL_PASS" else "BLOCKED：至少一项入口、日常输入、数据库只读边界或效果状态核对失败。",
        "known_limits": [
            "本次只执行 --dry-run，没有提交生产 job、没有发布新 release。",
            "P10-03 效果观察仍受真实样本门槛约束，不能由 dry-run 推导效果或收益结论。",
            "旧表继续保留，只有 V3 开发与旧页面迁移完成后才逐表重新裁决。",
        ],
        "next_stage": "V3_DAILY_OPERATION_AND_P10_03_EFFECT_OBSERVATION",
        "safety": {
            "production_database_written": False,
            "tdx_inputs_modified": False,
            "external_online_fetch": False,
            "production_run_published": False,
        },
    }
    atomic_write(payload)
    print(json.dumps({"status": status, "daily_status": daily.get("status"), "resolved_cutoff_date": daily.get("resolved_cutoff_date"), "next_stage": payload["next_stage"]}, ensure_ascii=False))
    return 0 if status == "FULL_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
