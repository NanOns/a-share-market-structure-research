"""Verify the P11-01 storage stop-growth gate from completed evidence.

This is a read-only gate composition.  It does not rerun a production build,
does not rewrite the initial P11-01 receipt, does not create a backup and does
not switch the runtime primary entry.  It proves that the current evidence
chain is sufficient to hand the project to the separately authorized P11-04
entry-handoff step.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data/database/market_research.duckdb"
ENTRY_PATH = ROOT / "runtime/workbench_entry.json"
SPEC_PATH = ROOT / "docs/WORKBENCH_DUAL_TRACK_IMPLEMENTATION_SPEC_V3.md"
REPORT_PATH = ROOT / "reports/upgrade_v3/P11-01-STORAGE-STOP-GROWTH-GATE-20260913.json"

REPORTS = {
    "p11_01": ROOT / "reports/upgrade_v3/P11-01-FINAL-ACCEPTANCE.json",
    "p11_02": ROOT / "reports/upgrade_v3/P11-02-OLD-WRITE-RECOVERY-PREVIEW.json",
    "storage_audit": ROOT / "reports/upgrade_v3/P11-02-AUD-STORAGE-REFERENCE-GRAPH-20260913.json",
    "auxiliary_audit": ROOT / "reports/upgrade_v3/P11-02-AUD-AUXILIARY-WRITES-BOUNDARY-20260913.json",
    "recovery": ROOT / "reports/upgrade_v3/P11-03-RECOVERY-EXECUTION-20260913.json",
    "table_retention": ROOT / "reports/upgrade_v3/P11-03-OLD-TABLE-RETENTION-DECISION-20260913.json",
}

CONTRACT_VERSION = "V3_P11_STORAGE_STOP_GROWTH_GATE_V1_0"


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


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected object JSON: {path}")
    return value


def main() -> int:
    reports = {name: _read_json(path) for name, path in REPORTS.items()}
    db_before = DB_PATH.stat()
    entry = _read_json(ENTRY_PATH)
    db_after = DB_PATH.stat()

    p11_01 = reports["p11_01"]
    p11_02 = reports["p11_02"]
    storage_audit = reports["storage_audit"]
    auxiliary_audit = reports["auxiliary_audit"]
    recovery = reports["recovery"]
    table_retention = reports["table_retention"]

    checks = {
        "p11_01_function_data_performance_pass": all(
            p11_01.get("acceptance", {}).get(name) == "FULL_PASS"
            for name in ("functional", "data_correctness", "performance")
        ),
        "p11_01_same_input_repeat_is_idempotent": p11_01.get("checks", {}).get(
            "same_input_repeat_adds_zero_content"
        )
        is True,
        "p11_01_initial_database_stat_unchanged": p11_01.get("checks", {}).get(
            "production_database_unchanged"
        )
        is True,
        "p11_02_migrated_domain_old_writes_stopped": p11_02.get("checks", {}).get(
            "migrated_domain_old_writes_stopped"
        )
        is True,
        "p11_02_current_reads_and_bindings_compatible": all(
            p11_02.get("checks", {}).get(name) is True
            for name in (
                "legacy_read_api_compatible",
                "relation_resolver_compatible",
                "migrated_result_bindings_complete",
            )
        ),
        "auxiliary_legacy_writers_have_bounded_boundaries": (
            auxiliary_audit.get("status") == "FULL_PASS"
            and auxiliary_audit.get("audit_disposition")
            == "RESOLVED_WITH_BOUNDED_LEGACY_WRITER_BOUNDARY"
        ),
        "storage_reference_graph_fully_reconciled": (
            storage_audit.get("status") == "FULL_PASS"
            and storage_audit.get("audit_disposition")
            == "RESOLVED_AS_CURRENT_OR_HISTORICAL_REFERENCE_NO_AUTO_ACTION"
        ),
        "recovery_result_truthfully_registered": (
            recovery.get("status") == "FULL_PASS"
            and recovery.get("postconditions", {}).get("all_authorized_targets_absent") is True
            and recovery.get("postconditions", {}).get("no_table_deletion") is True
            and recovery.get("missing_after_delete") == []
        ),
        "old_tables_retention_decision_registered": (
            table_retention.get("status") == "FULL_PASS"
            and table_retention.get("user_decision", {}).get("decision")
            == "RETAIN_ALL_LEGACY_TABLES"
        ),
        "database_stat_unchanged_during_gate": (
            db_before.st_size == db_after.st_size
            and db_before.st_mtime_ns == db_after.st_mtime_ns
        ),
        "runtime_entry_still_preserves_current_primary": (
            entry.get("primary_entry", {}).get("route") == "/v2"
            and entry.get("legacy_route_preserved") is True
        ),
    }

    target_route = "/v3"
    report = {
        "contract_version": CONTRACT_VERSION,
        "status": "FULL_PASS" if all(checks.values()) else "DEGRADED_PASS",
        "stage": "P11-01 storage stop-growth gate",
        "checks": checks,
        "storage_stop_growth": {
            "status": "FULL_PASS" if all(checks.values()) else "DEGRADED_PASS",
            "basis": [
                "same-input repeat adds zero business facts, identity/log rows and physical content",
                "migrated six-domain old writer callsites are stopped",
                "auxiliary writers are explicitly bounded and retained",
                "all storage catalog rows have current or historical provenance",
            ],
            "physical_recovery": "NOT_REASSERTED_BY_THIS_GATE",
            "old_table_cleanup": "NOT_IN_SCOPE",
        },
        "evidence": {
            name: {
                "path": str(path),
                "status": reports[name].get("status"),
                "contract_version": reports[name].get("contract_version"),
            }
            for name, path in REPORTS.items()
        },
        "runtime_entry": {
            "path": str(ENTRY_PATH),
            "read_only": True,
            "current_primary_entry": entry.get("primary_entry"),
            "target_p11_04_entry": {
                "route": target_route,
                "switch_executed": False,
                "authorization_required_for_mutation": True,
            },
        },
        "database_read_boundary": {
            "path": str(DB_PATH),
            "read_only": True,
            "before": {"size": db_before.st_size, "mtime_ns": db_before.st_mtime_ns},
            "after": {"size": db_after.st_size, "mtime_ns": db_after.st_mtime_ns},
        },
        "safety": {
            "production_database_mutated": False,
            "runtime_entry_mutated": False,
            "tdx_accessed": False,
            "cleanup_executed": False,
            "backup_created": False,
            "old_tables_deleted": False,
        },
        "known_limits": [
            "P10-03 remains EFFECT_OBSERVATION_PENDING; this gate does not claim algorithmic effect.",
            "Old tables remain retained until V3 development and old-page migration finish, per user decision.",
            "All previous physical backups are already deleted by the separately authorized P11-03 execution; this gate does not create a replacement backup.",
        ],
        "spec_path": str(SPEC_PATH),
        "spec_sha256": _sha256(SPEC_PATH),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "next_stage": "P11-04 explicit main-entry handoff",
    }
    _atomic_json(REPORT_PATH, report)
    print(json.dumps({"status": report["status"], "checks": checks, "report": str(REPORT_PATH)}, ensure_ascii=False))
    return 0 if report["status"] == "FULL_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
