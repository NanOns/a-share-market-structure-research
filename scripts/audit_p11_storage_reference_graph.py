"""Reconcile P11-02 storage references without changing production state.

The first P11-02 preview compared ``storage_objects.referenced`` with only
the current publication head.  This follow-up expands the read-only graph to
historical analysis slices, successful snapshots, active jobs/leases and the
online payload table.  It classifies every catalog row before any future
retention decision; it never clears a flag, mutates DuckDB, deletes a file or
executes a cleanup job.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data/database/market_research.duckdb"
SPEC_PATH = ROOT / "docs/WORKBENCH_DUAL_TRACK_IMPLEMENTATION_SPEC_V3.md"
P11_02_REPORT = ROOT / "reports/upgrade_v3/P11-02-OLD-WRITE-RECOVERY-PREVIEW.json"
REPORT_PATH = ROOT / "reports/upgrade_v3/P11-02-AUD-STORAGE-REFERENCE-GRAPH-20260913.json"

CONTRACT_VERSION = "V3_P11_STORAGE_REFERENCE_GRAPH_AUDIT_V1_0"
TOMBSTONE_ID = "analysis-obj-a9e40beba3799626c3a5b522f3644c480b16511ddd6b3ec76077eab5f1b1f6ce"


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


def _table_exists(connection: duckdb.DuckDBPyConnection, name: str) -> bool:
    return bool(
        connection.execute(
            "select count(*) from information_schema.tables where table_schema='main' and table_name=?",
            [name],
        ).fetchone()[0]
    )


def _load_payload(raw: Any, object_id: str | None = None) -> dict[str, Any]:
    try:
        value = json.loads(raw or "{}")
    except (TypeError, json.JSONDecodeError):
        value = {}
    if not isinstance(value, dict):
        value = {}
    if object_id and "storage_object_id" not in value:
        value["storage_object_id"] = object_id
    return value


def _relative_path_evidence(payload: dict[str, Any]) -> dict[str, Any]:
    relative = payload.get("relative_path")
    if not isinstance(relative, str) or not relative:
        return {
            "relative_path": None,
            "resolved_path": None,
            "exists": None,
            "path_evidence": "NO_EXTERNAL_PATH_EXPECTED",
        }
    candidate = (ROOT / Path(relative)).resolve(strict=False)
    inside_root = candidate == ROOT or ROOT in candidate.parents
    exists = bool(inside_root and candidate.is_file())
    return {
        "relative_path": relative,
        "resolved_path": str(candidate),
        "exists": exists,
        "path_evidence": "EXISTS" if exists else "MISSING_OR_OUTSIDE_MANAGED_ROOT",
    }


def _active_job_references(
    connection: duckdb.DuckDBPyConnection,
    slices_by_id: dict[str, dict[str, Any]],
) -> tuple[set[str], list[dict[str, Any]]]:
    refs: set[str] = set()
    evidence: list[dict[str, Any]] = []
    if not _table_exists(connection, "jobs"):
        return refs, evidence
    rows = connection.execute(
        "select job_id,status,payload_json from jobs where status in ('QUEUED','RUNNING','INTERRUPTED')"
    ).fetchall()
    for job_id, status, raw in rows:
        payload = _load_payload(raw)
        direct = payload.get("pending_storage_object_ids", [])
        direct_ids = [str(item) for item in direct] if isinstance(direct, list) else []
        slice_ids = payload.get("completed_slice_ids", [])
        slice_ids = [str(item) for item in slice_ids] if isinstance(slice_ids, list) else []
        derived_ids = sorted(
            {
                str(slices_by_id[slice_id]["storage_object_id"])
                for slice_id in slice_ids
                if slice_id in slices_by_id and slices_by_id[slice_id].get("storage_object_id")
            }
        )
        refs.update(direct_ids)
        refs.update(derived_ids)
        evidence.append(
            {
                "job_id": str(job_id),
                "status": str(status),
                "direct_storage_object_ids": sorted(set(direct_ids)),
                "completed_slice_ids": sorted(set(slice_ids)),
                "derived_storage_object_ids": derived_ids,
            }
        )
    return refs, evidence


def _active_lease_references(
    connection: duckdb.DuckDBPyConnection,
) -> tuple[set[str], list[dict[str, Any]]]:
    refs: set[str] = set()
    evidence: list[dict[str, Any]] = []
    if not _table_exists(connection, "leases"):
        return refs, evidence
    now = datetime.now(timezone.utc)
    for lease_id, raw in connection.execute("select lease_id,payload_json from leases").fetchall():
        payload = _load_payload(raw)
        if payload.get("state") != "ACTIVE":
            continue
        expires = payload.get("expires_at_utc") or payload.get("lease_until_utc")
        try:
            active = bool(
                expires
                and datetime.fromisoformat(str(expires).replace("Z", "+00:00")) > now
            )
        except ValueError:
            active = False
        if not active:
            continue
        object_ids = payload.get("storage_object_ids", [])
        object_ids = [str(item) for item in object_ids] if isinstance(object_ids, list) else []
        refs.update(object_ids)
        evidence.append(
            {
                "lease_id": str(lease_id),
                "expires_at": str(expires),
                "storage_object_ids": sorted(set(object_ids)),
            }
        )
    return refs, evidence


def _path_evidence_is_expected_tombstone(object_id: str, payload: dict[str, Any], path: dict[str, Any]) -> bool:
    tombstones = payload.get("legacy_slice_tombstones")
    return (
        object_id == TOMBSTONE_ID
        and payload.get("state") == "DELETED"
        and payload.get("physical_artifact_removed") is True
        and isinstance(tombstones, list)
        and bool(tombstones)
        and path.get("exists") is False
    )


def main() -> int:
    started = time.perf_counter()
    prior = json.loads(P11_02_REPORT.read_text(encoding="utf-8"))
    before_stat = DB_PATH.stat()

    with duckdb.connect(str(DB_PATH), read_only=True) as connection:
        catalog_rows = (
            connection.execute(
                "select storage_object_id,payload_json from storage_objects order by storage_object_id"
            ).fetchall()
            if _table_exists(connection, "storage_objects")
            else []
        )

        slices_by_id: dict[str, dict[str, Any]] = {}
        slices_by_object: dict[str, list[dict[str, Any]]] = defaultdict(list)
        if _table_exists(connection, "analysis_slices"):
            for row in connection.execute(
                """
                select slice_id,domain,trade_date,contract_id,storage_object_id,storage_kind
                from analysis_slices
                where storage_object_id is not null
                order by trade_date,slice_id
                """
            ).fetchall():
                slice_id, domain, trade_date, contract_id, object_id, storage_kind = row
                item = {
                    "slice_id": str(slice_id),
                    "domain": str(domain),
                    "trade_date": str(trade_date),
                    "contract_id": str(contract_id),
                    "storage_object_id": str(object_id),
                    "storage_kind": str(storage_kind),
                }
                slices_by_id[item["slice_id"]] = item
                slices_by_object[item["storage_object_id"]].append(item)

        current_publication_refs: dict[str, list[dict[str, Any]]] = defaultdict(list)
        if all(
            _table_exists(connection, table)
            for table in (
                "publication_analysis_snapshots",
                "analysis_snapshots",
                "analysis_snapshot_entries",
                "analysis_slices",
            )
        ):
            rows = connection.execute(
                """
                select distinct p.publication_id,p.snapshot_id,p.domain,e.slice_id,s.storage_object_id
                from publication_analysis_snapshots p
                join analysis_snapshots a
                  on a.snapshot_id=p.snapshot_id and a.status='SUCCESS'
                join analysis_snapshot_entries e on e.snapshot_id=a.snapshot_id
                join analysis_slices s on s.slice_id=e.slice_id
                where s.storage_object_id is not null
                order by p.publication_id,p.snapshot_id,p.domain,e.slice_id
                """
            ).fetchall()
            for publication_id, snapshot_id, domain, slice_id, object_id in rows:
                current_publication_refs[str(object_id)].append(
                    {
                        "publication_id": str(publication_id),
                        "snapshot_id": str(snapshot_id),
                        "domain": str(domain),
                        "slice_id": str(slice_id),
                    }
                )

        successful_snapshot_refs: dict[str, list[dict[str, Any]]] = defaultdict(list)
        if all(
            _table_exists(connection, table)
            for table in ("analysis_snapshots", "analysis_snapshot_entries", "analysis_slices")
        ):
            rows = connection.execute(
                """
                select distinct a.snapshot_id,a.status,e.slice_id,s.storage_object_id
                from analysis_snapshots a
                join analysis_snapshot_entries e on e.snapshot_id=a.snapshot_id
                join analysis_slices s on s.slice_id=e.slice_id
                where a.status='SUCCESS' and s.storage_object_id is not null
                order by a.snapshot_id,e.slice_id
                """
            ).fetchall()
            for snapshot_id, status, slice_id, object_id in rows:
                successful_snapshot_refs[str(object_id)].append(
                    {
                        "snapshot_id": str(snapshot_id),
                        "status": str(status),
                        "slice_id": str(slice_id),
                    }
                )

        online_payload_refs: dict[str, int] = {}
        if _table_exists(connection, "online_payloads"):
            online_payload_refs = {
                str(object_id): int(count)
                for object_id, count in connection.execute(
                    """
                    select storage_object_id,count(*)
                    from online_payloads
                    where storage_object_id is not null
                    group by storage_object_id
                    """
                ).fetchall()
            }

        active_job_refs, active_job_evidence = _active_job_references(connection, slices_by_id)
        active_lease_refs, active_lease_evidence = _active_lease_references(connection)

    after_stat = DB_PATH.stat()
    independent_items = prior.get("independent_audit_items", [])
    storage_audit_item = next(
        (
            item
            for item in independent_items
            if item.get("audit_item") == "P11-02-AUD-STORAGE-01"
        ),
        {},
    )
    prior_stale_flags = set(
        storage_audit_item.get("evidence", {}).get("stale_referenced_flags", [])
    )
    if not prior_stale_flags:
        prior_stale_flags = set(
            prior.get("storage_audit", {}).get("stale_referenced_flags", [])
        )
    if not prior_stale_flags:
        # The P11-02 report carries the audit under the top-level storage gate.
        prior_stale_flags = set(prior.get("storage_gate", {}).get("stale_referenced_flags", []))

    classified: list[dict[str, Any]] = []
    classifications: dict[str, list[str]] = defaultdict(list)
    for object_id, raw in catalog_rows:
        object_id = str(object_id)
        payload = _load_payload(raw, object_id)
        slice_refs = slices_by_object.get(object_id, [])
        current_refs = current_publication_refs.get(object_id, [])
        success_refs = successful_snapshot_refs.get(object_id, [])
        path = _relative_path_evidence(payload)

        if _path_evidence_is_expected_tombstone(object_id, payload, path):
            classification = "TOMBSTONE_EXPECTED_ABSENT"
            disposition = "RETAIN_TOMBSTONE_NO_PHYSICAL_RECOVERY"
        elif current_refs:
            classification = "CURRENT_PUBLICATION_REFERENCED"
            disposition = "RETAIN_PROTECTED"
        elif object_id in active_job_refs:
            classification = "ACTIVE_JOB_REFERENCED"
            disposition = "RETAIN_PROTECTED"
        elif object_id in active_lease_refs:
            classification = "ACTIVE_LEASE_REFERENCED"
            disposition = "RETAIN_PROTECTED"
        elif object_id in online_payload_refs:
            classification = "ONLINE_PAYLOAD_REFERENCED"
            disposition = "RETAIN_PROTECTED"
        elif success_refs or slice_refs:
            classification = "HISTORICAL_ANALYSIS_SLICE_REFERENCED"
            disposition = "RETAIN_UNTIL_EXPLICIT_RETENTION_DECISION"
        elif payload.get("referenced") is True:
            classification = "REFERENCED_FLAG_WITHOUT_KNOWN_ROW_GRAPH"
            disposition = "RETAIN_PENDING_RECONCILIATION"
        else:
            classification = "UNREFERENCED_CATALOG_ROW"
            disposition = "NO_AUTOMATIC_ACTION"

        item = {
            "storage_object_id": object_id,
            "kind": payload.get("kind"),
            "state": payload.get("state"),
            "storage_kind": payload.get("storage_kind"),
            "referenced_flag": payload.get("referenced") is True,
            "classification": classification,
            "retention_disposition": disposition,
            "current_publication_references": current_refs,
            "successful_snapshot_references": success_refs,
            "analysis_slice_references": slice_refs,
            "active_job_reference": object_id in active_job_refs,
            "active_lease_reference": object_id in active_lease_refs,
            "online_payload_reference_count": online_payload_refs.get(object_id, 0),
            "physical_path": path,
            "payload_path": payload.get("path"),
            "legacy_slice_tombstones": payload.get("legacy_slice_tombstones", []),
        }
        classified.append(item)
        classifications[classification].append(object_id)

    stale_flags_classified_historically = sorted(
        object_id
        for object_id in prior_stale_flags
        if any(
            item["storage_object_id"] == object_id
            and item["classification"] == "HISTORICAL_ANALYSIS_SLICE_REFERENCED"
            for item in classified
        )
    )
    unresolved_flagged = sorted(
        item["storage_object_id"]
        for item in classified
        if item["referenced_flag"]
        and item["classification"] == "REFERENCED_FLAG_WITHOUT_KNOWN_ROW_GRAPH"
    )
    unexpected_missing_files = sorted(
        item["storage_object_id"]
        for item in classified
        if item["physical_path"]["path_evidence"] == "MISSING_OR_OUTSIDE_MANAGED_ROOT"
        and item["classification"] != "TOMBSTONE_EXPECTED_ABSENT"
    )
    tombstone_items = [
        item for item in classified if item["classification"] == "TOMBSTONE_EXPECTED_ABSENT"
    ]

    checks = {
        "p11_02_precondition": prior.get("contract_version") == "V3_P11_OLD_WRITE_RECOVERY_PREVIEW_V1_0",
        "catalog_rows_all_classified": len(classified) == len(catalog_rows) and len(classified) == 52,
        "current_publication_reference_graph_captured": len(current_publication_refs) == 34,
        "all_prior_stale_flags_have_historical_provenance": (
            len(prior_stale_flags) == 17
            and stale_flags_classified_historically == sorted(prior_stale_flags)
        ),
        "no_flagged_object_without_known_row_graph": not unresolved_flagged,
        "active_job_and_lease_graph_checked": not active_job_refs and not active_lease_refs,
        "online_payload_graph_checked": not online_payload_refs,
        "tombstone_expected_absence_proven": bool(
            len(tombstone_items) == 1
            and tombstone_items[0]["storage_object_id"] == TOMBSTONE_ID
            and tombstone_items[0]["physical_path"]["exists"] is False
            and tombstone_items[0]["legacy_slice_tombstones"]
        ),
        "no_unexpected_missing_physical_artifact": not unexpected_missing_files,
        "production_db_stat_unchanged": (
            before_stat.st_size == after_stat.st_size
            and before_stat.st_mtime_ns == after_stat.st_mtime_ns
        ),
    }

    report = {
        "contract_version": CONTRACT_VERSION,
        "status": "FULL_PASS" if all(checks.values()) else "DEGRADED_PASS",
        "stage": "P11-02 independent storage reference graph audit",
        "audit_item": "P11-02-AUD-STORAGE-01",
        "audit_disposition": (
            "RESOLVED_AS_CURRENT_OR_HISTORICAL_REFERENCE_NO_AUTO_ACTION"
            if all(checks.values())
            else "OPEN_RECONCILIATION_GAP"
        ),
        "checks": checks,
        "catalog_summary": {
            "storage_object_count": len(classified),
            "classification_counts": {
                key: len(value) for key, value in sorted(classifications.items())
            },
            "current_publication_reference_count": len(current_publication_refs),
            "successful_snapshot_reference_count": len(successful_snapshot_refs),
            "historical_slice_reference_count": len(slices_by_object),
            "prior_stale_referenced_flag_count": len(prior_stale_flags),
            "prior_stale_flags_classified_historically": len(stale_flags_classified_historically),
        },
        "reference_graph": {
            "current_publication_references": {
                key: value for key, value in sorted(current_publication_refs.items())
            },
            "active_job_evidence": active_job_evidence,
            "active_lease_evidence": active_lease_evidence,
            "online_payload_reference_counts": online_payload_refs,
        },
        "items": classified,
        "issues": {
            "prior_stale_referenced_flags": sorted(prior_stale_flags),
            "stale_flags_classified_historically": stale_flags_classified_historically,
            "flagged_objects_without_known_row_graph": unresolved_flagged,
            "unexpected_missing_physical_artifact": unexpected_missing_files,
            "tombstone_expected_absent": [item["storage_object_id"] for item in tombstone_items],
        },
        "storage_decision": {
            "automatic_action": "NONE",
            "clear_referenced_flags": False,
            "delete_storage_objects": False,
            "delete_physical_artifacts": False,
            "reason": (
                "All stale flags are historical result-row slice provenance; current objects remain protected, "
                "and the one missing physical artifact is an explicitly recorded deleted tombstone."
            ),
        },
        "database_read_boundary": {
            "path": str(DB_PATH),
            "read_only": True,
            "before": {"size": before_stat.st_size, "mtime_ns": before_stat.st_mtime_ns},
            "after": {"size": after_stat.st_size, "mtime_ns": after_stat.st_mtime_ns},
        },
        "safety": {
            "production_mutation_executed": False,
            "tdx_accessed": False,
            "tdx_mutated": False,
            "cleanup_executed": False,
            "physical_artifact_deleted": False,
            "storage_object_flag_cleared": False,
        },
        "retention_boundary": {
            "decision": "RETAIN_ALL_LEGACY_TABLES",
            "reason": "User-directed old-table retention; this audit does not decide table cleanup.",
            "table_cleanup": "NOT_IN_SCOPE",
        },
        "spec_path": str(SPEC_PATH),
        "spec_sha256": _sha256(SPEC_PATH),
        "prior_report": str(P11_02_REPORT),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "runtime_seconds": round(time.perf_counter() - started, 3),
        "next_stage": "P11-01 storage stop-growth gate and P11-04 main-entry handoff",
    }
    _atomic_json(REPORT_PATH, report)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True, default=str))
    return 0 if report["status"] == "FULL_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
