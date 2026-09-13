"""Record the user decision to retain legacy tables until V3/UI migration ends."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data/database/market_research.duckdb"
SPEC_PATH = ROOT / "docs/WORKBENCH_DUAL_TRACK_IMPLEMENTATION_SPEC_V3.md"
P11_02_REPORT = ROOT / "reports/upgrade_v3/P11-02-OLD-WRITE-RECOVERY-PREVIEW.json"
REPORT_PATH = ROOT / "reports/upgrade_v3/P11-03-OLD-TABLE-RETENTION-DECISION-20260913.json"

TABLE_GROUPS = {
    "migrated_result_old_copies": (
        "stock_technical_daily",
        "stock_strength_daily",
        "stock_high_daily",
        "sector_member_state_daily",
        "historical_structure_daily",
        "stock_structure_summary_daily",
    ),
    "relation_old_copies": (
        "membership_snapshots",
        "membership_entries",
        "sector_membership_changes",
        "stock_sector_associations_daily",
    ),
    "auxiliary_unmigrated_result_tables": (
        "sector_base_daily",
        "historical_coverage_daily",
        "representative_state_daily",
        "sector_cycle_daily",
        "mainline_daily",
        "market_cycle_daily",
        "market_reference_daily",
    ),
}


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


def _db_boundary() -> dict[str, int]:
    stat = DB_PATH.stat()
    return {"size_bytes": stat.st_size, "mtime_ns": stat.st_mtime_ns}


def main() -> int:
    p11_02 = json.loads(P11_02_REPORT.read_text(encoding="utf-8"))
    domain_rows: dict[str, dict[str, Any]] = {}
    for item in p11_02["recovery_preview"]["result_old_copies"]["migrated_domains"]:
        domain_rows[item["legacy_table"]] = {
            "row_count": item["legacy"]["row_count"],
            "estimated_physical_bytes": item["legacy"]["estimated_physical_bytes"],
            "equivalence_status": item["equivalence_status"],
        }
    for item in p11_02["recovery_preview"]["relation_old_copies"]["old_relation_tables"]:
        domain_rows[item["table"]] = {
            "row_count": item["row_count"],
            "estimated_physical_bytes": item["estimated_physical_bytes"],
        }
    for item in p11_02["recovery_preview"]["result_old_copies"]["auxiliary_unmigrated_result_tables"]:
        domain_rows[item["table"]] = {
            "row_count": item["row_count"],
            "estimated_physical_bytes": item["estimated_physical_bytes"],
        }

    tables = []
    for group, names in TABLE_GROUPS.items():
        for table in names:
            tables.append(
                {
                    "group": group,
                    "table": table,
                    **domain_rows.get(table, {}),
                    "decision": "RETAIN_UNTIL_V3_AND_UI_MIGRATION_COMPLETE",
                    "actual_action": "NONE",
                    "deletion_authorized": False,
                }
            )
    before = _db_boundary()
    after = _db_boundary()
    report = {
        "contract_version": "V3_P11_OLD_TABLE_RETENTION_DECISION_V1_0",
        "status": "FULL_PASS",
        "stage": "P11-03",
        "user_decision": {
            "decision": "RETAIN_ALL_LEGACY_TABLES",
            "scope": "6 migrated-domain old tables, 4 relation history tables, and 7 auxiliary result tables",
            "condition": "Reassess table by table only after V3 development is complete and all old page functions are migrated.",
            "source": "explicit user instruction in current task",
        },
        "retained_table_count": len(tables),
        "retained_tables": tables,
        "reassessment_gates": [
            "V3 feature development complete",
            "all old page functions migrated to the V3 entry points",
            "each table's API/page/read consumers mapped",
            "per-table equivalence and compatibility regression passed",
            "storage reference audit closed or separately dispositioned",
            "a new explicit table-by-table deletion decision recorded",
        ],
        "database_read_boundary": {
            "path": str(DB_PATH),
            "before": before,
            "after": after,
            "unchanged": before == after,
            "read_only_decision_record": True,
        },
        "safety": {
            "database_mutated": False,
            "tables_deleted": False,
            "tdx_accessed": False,
            "tdx_mutated": False,
            "vacuum_executed": False,
        },
        "spec_path": str(SPEC_PATH),
        "spec_sha256": _sha256(SPEC_PATH),
        "prior_stage": str(P11_02_REPORT),
        "next_stage": "V3_COMPLETION_AND_UI_MIGRATION_GATE",
        "next_stage_gate": "Do not reassess or delete a legacy table before all listed gates and a new explicit per-table decision are complete.",
        "generated_at_local": "2026-09-13",
    }
    _atomic_json(REPORT_PATH, report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
