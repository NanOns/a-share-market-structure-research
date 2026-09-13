"""P11-03 read-only recovery decision register.

P11-03 has no physical-recovery authorization in the current task context.
This verifier therefore registers every exact object from the P11-02 preview
as WAITING_DECISION and proves that the production database remains unchanged.
It never deletes, moves, vacuums, backs up, restores, or writes to TDX.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any

import duckdb


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data/database/market_research.duckdb"
SPEC_PATH = ROOT / "docs/WORKBENCH_DUAL_TRACK_IMPLEMENTATION_SPEC_V3.md"
P11_02_REPORT = ROOT / "reports/upgrade_v3/P11-02-OLD-WRITE-RECOVERY-PREVIEW.json"
P11_01_REPORT = ROOT / "reports/upgrade_v3/P11-01-FINAL-ACCEPTANCE.json"
REPORT_PATH = ROOT / "reports/upgrade_v3/P11-03-RECOVERY-WAITING-DECISION.json"

CONTRACT_VERSION = "V3_P11_RECOVERY_WAITING_DECISION_V1_0"
P11_02_CONTRACT = "V3_P11_OLD_WRITE_RECOVERY_PREVIEW_V1_0"
WAITING_DECISION = "WAITING_DECISION"
NO_ACTION = "NONE"
AUTHORIZATION = "P11-03_EXPLICIT_RANGE_AUTHORIZATION"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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


def _file_boundary() -> dict[str, int]:
    stat = DB_PATH.stat()
    return {"size_bytes": stat.st_size, "mtime_ns": stat.st_mtime_ns}


def _read_only_database_boundary() -> dict[str, Any]:
    before = _file_boundary()
    with duckdb.connect(str(DB_PATH), read_only=True) as connection:
        connection.execute("SELECT 1").fetchone()
        database_size = connection.execute("PRAGMA database_size").fetchone()
        columns = [item[0] for item in connection.description]
    after = _file_boundary()
    return {
        "path": str(DB_PATH),
        "read_only": True,
        "before": before,
        "after": after,
        "unchanged": before == after,
        "pragma_database_size": dict(zip(columns, database_size)),
    }


def _with_decision(item: dict[str, Any], *, object_kind: str, target: str) -> dict[str, Any]:
    return {
        "object_kind": object_kind,
        "target": target,
        "exact_object": item,
        "proposed_action": WAITING_DECISION,
        "required_authorization": AUTHORIZATION,
        "actual_action": NO_ACTION,
        "reclaimed_bytes": 0,
    }


def _target_is_exact(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    normalized = value.replace("\\", "/").rstrip("/").lower()
    broad_targets = {
        "data",
        "data/",
        "runtime",
        "runtime/",
        "data/input_staging",
        "data/input_staging/extracted",
        "data/backups",
    }
    return normalized not in broad_targets


def _build_register(preview: dict[str, Any]) -> dict[str, Any]:
    register: dict[str, list[dict[str, Any]]] = {
        "relation_old_copies": [],
        "migrated_result_old_copies": [],
        "auxiliary_result_tables": [],
        "extracted_directories": [],
        "metadata_snapshots": [],
        "source_packages": [],
        "phase1_cache": [],
        "backup_objects": [],
        "runtime_artifacts": [],
    }

    for item in preview["relation_old_copies"]["old_relation_tables"]:
        register["relation_old_copies"].append(
            _with_decision(item, object_kind="DUCKDB_TABLE", target=item["table"])
        )

    for domain in preview["result_old_copies"]["migrated_domains"]:
        item = domain["legacy"] | {
            "domain": domain["domain"],
            "equivalence_status": domain["equivalence_status"],
            "legacy_table": domain["legacy_table"],
            "recovery_status": domain["recovery_status"],
        }
        register["migrated_result_old_copies"].append(
            _with_decision(item, object_kind="DUCKDB_TABLE", target=item["table"])
        )

    for item in preview["result_old_copies"]["auxiliary_unmigrated_result_tables"]:
        register["auxiliary_result_tables"].append(
            _with_decision(item, object_kind="DUCKDB_TABLE", target=item["table"])
        )

    extraction = preview["extraction_cache"]
    for item in extraction["extracted"]:
        register["extracted_directories"].append(
            _with_decision(item, object_kind="DIRECTORY", target=item["root"])
        )
    for item in extraction["metadata_snapshots"]:
        register["metadata_snapshots"].append(
            _with_decision(item, object_kind="DIRECTORY", target=item["root"])
        )
    for item in extraction["source_packages"]:
        register["source_packages"].append(
            _with_decision(item, object_kind="FILE", target=item["path"])
        )
    register["phase1_cache"].append(
        _with_decision(extraction["phase1_cache"], object_kind="DIRECTORY", target=extraction["phase1_cache"]["root"])
    )

    for item in preview["backups"]["items"]:
        register["backup_objects"].append(
            _with_decision(item, object_kind=item["item_type"], target=item["path"])
        )
    for item in preview["runtime_artifacts"]["items"]:
        register["runtime_artifacts"].append(
            _with_decision(item, object_kind="FILE", target=item["path"])
        )
    return register


def _validate_register(register: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    counts = {key: len(value) for key, value in register.items()}
    entries = [entry for values in register.values() for entry in values]
    exact_targets = all(_target_is_exact(entry["target"]) for entry in entries)
    no_action = all(
        entry["proposed_action"] == WAITING_DECISION
        and entry["required_authorization"] == AUTHORIZATION
        and entry["actual_action"] == NO_ACTION
        and entry["reclaimed_bytes"] == 0
        for entry in entries
    )
    unique_targets = len({entry["target"] for entry in entries}) == len(entries)
    return {
        "entry_count": len(entries),
        "counts_by_class": counts,
        "exact_targets": exact_targets,
        "no_action_recorded": no_action,
        "unique_targets": unique_targets,
        "non_empty": bool(entries),
    }


def main() -> int:
    started = time.perf_counter()
    p11_02 = json.loads(P11_02_REPORT.read_text(encoding="utf-8"))
    p11_01 = json.loads(P11_01_REPORT.read_text(encoding="utf-8"))
    spec_sha256 = _sha256(SPEC_PATH)
    preview = p11_02["recovery_preview"]
    register = _build_register(preview)
    register_validation = _validate_register(register)
    database_boundary = _read_only_database_boundary()
    audits = p11_02.get("independent_audit_items", [])
    checks = {
        "p11_01_precondition": p11_01.get("status") in {"FULL_PASS", "DEGRADED_PASS"},
        "p11_02_precondition": p11_02.get("contract_version") == P11_02_CONTRACT
        and p11_02.get("status") in {"FULL_PASS", "DEGRADED_PASS"},
        "current_preview_has_no_authorized_recovery": preview.get("deletion_authorized") is False
        and preview.get("reclaimable_bytes_now") == 0,
        "exact_targets_registered": register_validation["non_empty"]
        and register_validation["exact_targets"]
        and register_validation["unique_targets"],
        "all_actions_are_waiting_decision": register_validation["no_action_recorded"],
        "production_database_unchanged": database_boundary["unchanged"],
        "independent_audits_carried_forward": len(audits) >= 2
        and all(item.get("status") == "OPEN" for item in audits),
    }
    report = {
        "acceptance": {
            "decision_register": "FULL_PASS" if all(checks.values()) else "DEGRADED_PASS",
            "physical_recovery": "NOT_AUTHORIZED",
            "storage": "DEGRADED_PASS",
        },
        "checks": checks,
        "contract_version": CONTRACT_VERSION,
        "database_read_boundary": database_boundary,
        "decision": {
            "status": WAITING_DECISION,
            "deletion_authorized": False,
            "physical_recovery_executed": False,
            "reclaimed_bytes": 0,
            "required_authorization": AUTHORIZATION,
            "reason": "The current task/document request does not authorize a physical recovery range.",
        },
        "evidence": {
            "runtime_seconds": round(time.perf_counter() - started, 3),
            "tdx_accessed": False,
            "production_mutation_executed": False,
            "forbidden_operations": ["DELETE", "MOVE", "VACUUM", "BACKUP", "RESTORE", "TDX_WRITE"],
        },
        "generated_at_local": "2026-09-13",
        "independent_audit_items": audits,
        "next_stage": "P11-04",
        "next_stage_gate": "Resolve the carried storage/auxiliary-writer audits and obtain an explicit range decision before any physical recovery or main-entry switch.",
        "prior_stage": {
            "report": str(P11_02_REPORT),
            "sha256": _sha256(P11_02_REPORT),
            "status": p11_02.get("status"),
        },
        "recovery_register": register,
        "register_validation": register_validation,
        "spec_path": str(SPEC_PATH),
        "spec_sha256": spec_sha256,
        "stage_contract": {
            "scope": "exact-object recovery decision registration after the P11-02 read-only preview",
            "purpose": "record WAITING_DECISION without physical deletion or recovery",
            "no_actions": ["DELETE", "MOVE", "VACUUM", "BACKUP", "RESTORE", "BUILD", "TDX_WRITE"],
            "authorization_boundary": AUTHORIZATION,
        },
        "status": "DEGRADED_PASS" if all(checks.values()) else "BLOCKED",
    }
    _atomic_json(REPORT_PATH, report)
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
