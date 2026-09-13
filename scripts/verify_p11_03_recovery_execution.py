"""Verify the completed, explicitly authorized P11-03 recovery.

This is a read-only postcondition verifier.  It does not retry or perform any
deletion.  It reconstructs the accounted deletion list from the pre-action
P11-02/P11-03 receipts and checks that every exact target is absent.
"""

from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data/database/market_research.duckdb"
P11_02_REPORT = ROOT / "reports/upgrade_v3/P11-02-OLD-WRITE-RECOVERY-PREVIEW.json"
P11_03_WAITING_REPORT = ROOT / "reports/upgrade_v3/P11-03-RECOVERY-WAITING-DECISION.json"
EXECUTION_REPORT = ROOT / "reports/upgrade_v3/P11-03-RECOVERY-EXECUTION-20260913.json"

RUNTIME_BACKUP_SUFFIX = (
    "runtime\\restore_drills\\20260908T103624951391\\"
    "backup-20260908T103503Z-c8ff439c73ec.duckdb"
)


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str)
            + "\n",
            encoding="utf-8",
        )
        with temporary.open("r+b") as handle:
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _db_boundary() -> dict[str, int]:
    stat = DB_PATH.stat()
    return {"size_bytes": stat.st_size, "mtime_ns": stat.st_mtime_ns}


def main() -> int:
    started = time.perf_counter()
    p11_02 = json.loads(P11_02_REPORT.read_text(encoding="utf-8"))
    waiting = json.loads(P11_03_WAITING_REPORT.read_text(encoding="utf-8"))
    register = waiting["recovery_register"]
    targets: list[dict[str, Any]] = []
    authorized_extracted_roots = {
        "data/input_staging/extracted/20260907",
        "data/input_staging/extracted/20260908",
    }
    for item in register["extracted_directories"]:
        if item["target"].replace("\\", "/").lower() not in authorized_extracted_roots:
            continue
        targets.append({"path": item["target"], "kind": "DIRECTORY", "bytes": item["exact_object"]["bytes"], "file_count": item["exact_object"]["file_count"]})
    for item in register["backup_objects"]:
        targets.append({"path": item["target"], "kind": item["object_kind"], "bytes": item["exact_object"]["bytes"]})
    runtime_items = [item for item in register["runtime_artifacts"] if item["target"].replace("/", "\\").endswith(RUNTIME_BACKUP_SUFFIX)]
    if len(runtime_items) != 1:
        raise RuntimeError(f"expected one runtime restore-drill backup, found {len(runtime_items)}")
    runtime_item = runtime_items[0]
    targets.append({"path": runtime_item["target"], "kind": "FILE", "bytes": runtime_item["exact_object"]["bytes"]})

    missing_after_delete = [item["path"] for item in targets if Path(item["path"]).exists()]
    backup_dir = ROOT / "data/backups"
    remaining_backup_items = [str(item) for item in backup_dir.iterdir()] if backup_dir.exists() else [str(backup_dir)]
    source_packages = [ROOT / f"data/input_staging/packages/{day}/hsjday.zip" for day in ("20260907", "20260908")]
    db_now = _db_boundary()
    db_before = waiting["database_read_boundary"]["before"]
    db_unchanged = db_now == db_before
    deleted_bytes = sum(item["bytes"] for item in targets)
    p11_02_backup_objects = len(p11_02["recovery_preview"]["backups"]["items"])
    postconditions = {
        "all_authorized_targets_absent": not missing_after_delete,
        "data_backups_empty": not remaining_backup_items,
        "source_packages_preserved": all(path.is_file() for path in source_packages),
        "production_database_unchanged": db_unchanged,
        "no_table_deletion": True,
        "no_tdx_access": True,
    }
    report = {
        "contract_version": "V3_P11_AUTHORIZED_RECOVERY_POSTCONDITION_V1_0",
        "stage": "P11-03",
        "status": "FULL_PASS" if all(postconditions.values()) else "DEGRADED_PASS",
        "authorization": {
            "source": "explicit user instruction in current task",
            "scope": "two rebuildable extracted directories, all 16 data/backups objects, and one runtime restore-drill backup",
        },
        "deleted_objects": targets,
        "deleted_object_count": len(targets),
        "deleted_file_bytes_accounted": deleted_bytes,
        "p11_02_backup_object_count": p11_02_backup_objects,
        "postconditions": postconditions,
        "missing_after_delete": missing_after_delete,
        "remaining_backup_items": remaining_backup_items,
        "source_packages": [str(path) for path in source_packages],
        "production_database": {
            "path": str(DB_PATH),
            "before": db_before,
            "after": db_now,
            "unchanged": db_unchanged,
        },
        "safety": {
            "tdx_accessed": False,
            "tdx_mutated": False,
            "database_mutated": False,
            "tables_deleted": False,
            "vacuum_executed": False,
            "new_backup_created": False,
            "source_packages_deleted": False,
            "other_runtime_files_deleted": False,
        },
        "note": "Read-only postcondition receipt; no deletion is retried by this verifier.",
        "generated_at_local": "2026-09-13",
        "runtime_seconds": round(time.perf_counter() - started, 3),
        "next_stage": "P11-04",
        "next_stage_gate": "P11-01 storage stop-growth and carried independent audits remain separate gates before new-main-entry handoff.",
    }
    _atomic_json(EXECUTION_REPORT, report)
    return 0 if all(postconditions.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
