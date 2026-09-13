"""Execute the explicitly authorized P11-03 recovery range.

The target set is intentionally closed and path-checked.  This script only
deletes the two rebuildable extracted bundles, every object currently under
the audited data/backups directory, and one explicitly named restore-drill
backup.  It does not touch TDX, source packages, database tables, metadata,
cache, or other runtime files.
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data/database/market_research.duckdb"
BACKUP_DIR = ROOT / "data/backups"
P11_03_WAITING_REPORT = ROOT / "reports/upgrade_v3/P11-03-RECOVERY-WAITING-DECISION.json"
EXECUTION_REPORT = ROOT / "reports/upgrade_v3/P11-03-RECOVERY-EXECUTION-20260913.json"

EXTRACTED_TARGETS = (
    ROOT / "data/input_staging/extracted/20260907",
    ROOT / "data/input_staging/extracted/20260908",
)
SOURCE_PACKAGE_GUARDS = (
    ROOT / "data/input_staging/packages/20260907/hsjday.zip",
    ROOT / "data/input_staging/packages/20260908/hsjday.zip",
)
EXPECTED_BACKUP_NAMES = (
    "backup-20260910T121350Z-796244f7da16.objects",
    "backup-20260910T123432Z-8a899d477b09.objects",
    "backup-20260910T121350Z-796244f7da16.duckdb",
    "backup-20260910T121350Z-796244f7da16.manifest.json",
    "backup-20260910T123432Z-8a899d477b09.duckdb",
    "backup-20260910T123432Z-8a899d477b09.manifest.json",
    "backup-20260911T193112Z-7a931b0724e8.duckdb",
    "backup-20260911T233048Z-45d7b3c1bed2.duckdb",
    "backup-20260912T000023Z-65432baaf1ee.duckdb",
    "backup-20260912T002526Z-822de3d9b647.duckdb",
    "backup-20260912T004954Z-21dfb9a772b2.duckdb",
    "backup-20260912T010834Z-02efee63a95c.duckdb",
    "backup-20260912T012602Z-9a4b46c91b4d.duckdb",
    "backup-20260912T020156Z-638bdba5a42e.duckdb",
    "backup-20260912T023322Z-46f5b9f95f44.duckdb",
    "backup-20260912T030620Z-5f80d367e3dc.duckdb",
)
RUNTIME_BACKUP_TARGET = (
    ROOT
    / "runtime/restore_drills/20260908T103624951391/backup-20260908T103503Z-c8ff439c73ec.duckdb"
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


def _assert_in_workspace(path: Path) -> Path:
    workspace = ROOT.resolve()
    resolved = path.resolve(strict=False)
    if resolved == workspace or workspace not in resolved.parents:
        raise RuntimeError(f"refusing target outside workspace: {resolved}")
    if "new_tdx" in {part.lower() for part in resolved.parts}:
        raise RuntimeError(f"refusing TDX target: {resolved}")
    return resolved


def _stat(path: Path) -> dict[str, Any]:
    resolved = _assert_in_workspace(path)
    if resolved.is_file():
        return {"path": str(resolved), "kind": "FILE", "bytes": resolved.stat().st_size}
    if resolved.is_dir():
        files = [item for item in resolved.rglob("*") if item.is_file()]
        return {
            "path": str(resolved),
            "kind": "DIRECTORY",
            "file_count": len(files),
            "bytes": sum(item.stat().st_size for item in files),
        }
    raise FileNotFoundError(resolved)


def _db_boundary() -> dict[str, int]:
    stat = DB_PATH.stat()
    return {"size_bytes": stat.st_size, "mtime_ns": stat.st_mtime_ns}


def _delete_exact(path: Path) -> dict[str, Any]:
    before = _stat(path)
    resolved = Path(before["path"])
    if resolved.is_dir():
        shutil.rmtree(resolved)
    else:
        resolved.unlink()
    if resolved.exists():
        raise RuntimeError(f"target still exists after delete: {resolved}")
    return {**before, "actual_action": "DELETE", "reclaimed_bytes_accounted": before["bytes"]}


def main() -> int:
    started = time.perf_counter()
    waiting = json.loads(P11_03_WAITING_REPORT.read_text(encoding="utf-8"))
    if waiting["decision"]["status"] != "WAITING_DECISION":
        raise RuntimeError("P11-03 waiting-decision receipt is not the expected precondition")
    if waiting["decision"]["physical_recovery_executed"]:
        raise RuntimeError("P11-03 recovery was already recorded as executed")
    if not all(path.is_file() for path in SOURCE_PACKAGE_GUARDS):
        raise RuntimeError("rebuild source package guard is missing")

    direct_backup_items = list(BACKUP_DIR.iterdir())
    direct_backup_names = {item.name for item in direct_backup_items}
    expected_backup_names = set(EXPECTED_BACKUP_NAMES)
    if direct_backup_names != expected_backup_names:
        raise RuntimeError(
            "data/backups contents changed; refusing broad deletion: "
            f"expected={sorted(expected_backup_names)}, actual={sorted(direct_backup_names)}"
        )
    if not all(path.is_dir() for path in EXTRACTED_TARGETS):
        raise RuntimeError("one or more explicitly authorized extracted targets are missing")
    if not RUNTIME_BACKUP_TARGET.is_file():
        raise RuntimeError("explicitly authorized runtime restore-drill backup is missing")

    before_db = _db_boundary()
    disk_before = shutil.disk_usage(ROOT.anchor or ROOT.drive or str(ROOT))
    targets = list(EXTRACTED_TARGETS)
    targets.extend(BACKUP_DIR / name for name in EXPECTED_BACKUP_NAMES)
    targets.append(RUNTIME_BACKUP_TARGET)
    deleted = [_delete_exact(path) for path in targets]
    after_db = _db_boundary()
    disk_after = shutil.disk_usage(ROOT.anchor or ROOT.drive or str(ROOT))
    remaining_backup_items = [item.name for item in BACKUP_DIR.iterdir()]
    remaining_extracted = [str(path) for path in EXTRACTED_TARGETS if path.exists()]
    remaining_runtime_backup = str(RUNTIME_BACKUP_TARGET) if RUNTIME_BACKUP_TARGET.exists() else None
    report = {
        "contract_version": "V3_P11_AUTHORIZED_RECOVERY_EXECUTION_V1_0",
        "status": "FULL_PASS",
        "stage": "P11-03",
        "authorization": {
            "source": "explicit user instruction in current task",
            "authorized_ranges": [
                "data/input_staging/extracted/20260907",
                "data/input_staging/extracted/20260908",
                "all 16 pre-audited direct children of data/backups",
                "runtime/restore_drills/20260908T103624951391/backup-20260908T103503Z-c8ff439c73ec.duckdb",
            ],
        },
        "precondition": {
            "waiting_decision_report": str(P11_03_WAITING_REPORT),
            "source_packages_present": [str(path) for path in SOURCE_PACKAGE_GUARDS],
            "data_backups_exact_contents": True,
        },
        "deleted_objects": deleted,
        "deleted_object_count": len(deleted),
        "deleted_file_bytes_accounted": sum(item["reclaimed_bytes_accounted"] for item in deleted),
        "filesystem_free_bytes_before": disk_before.free,
        "filesystem_free_bytes_after": disk_after.free,
        "filesystem_free_delta_bytes": disk_after.free - disk_before.free,
        "postcondition": {
            "deleted_extracted_targets_absent": not remaining_extracted,
            "data_backups_empty": not remaining_backup_items,
            "deleted_runtime_backup_absent": remaining_runtime_backup is None,
            "remaining_backup_items": remaining_backup_items,
            "remaining_extracted_targets": remaining_extracted,
            "remaining_runtime_backup": remaining_runtime_backup,
        },
        "production_database": {
            "path": str(DB_PATH),
            "before": before_db,
            "after": after_db,
            "unchanged": before_db == after_db,
        },
        "safety": {
            "tdx_accessed": False,
            "tdx_mutated": False,
            "database_mutated": False,
            "tables_deleted": False,
            "vacuum_executed": False,
            "new_backup_created": False,
            "broad_root_deleted": False,
            "source_packages_deleted": False,
        },
        "generated_at_local": "2026-09-13",
        "runtime_seconds": round(time.perf_counter() - started, 3),
        "next_stage": "P11-04",
        "next_stage_gate": "P11-01 storage stop-growth and carried independent audits remain separate gates before new-main-entry handoff.",
    }
    postcondition_pass = all(
        (
            report["postcondition"]["deleted_extracted_targets_absent"],
            report["postcondition"]["data_backups_empty"],
            report["postcondition"]["deleted_runtime_backup_absent"],
            report["production_database"]["unchanged"],
        )
    )
    if not postcondition_pass:
        report["status"] = "DEGRADED_PASS"
        raise RuntimeError(json.dumps(report, ensure_ascii=False))
    _atomic_json(EXECUTION_REPORT, report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
