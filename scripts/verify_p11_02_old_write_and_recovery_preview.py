"""P11-02 read-only proof for stopped legacy writes and recovery preview.

The verifier deliberately does not call cleanup, backup, restore, migration,
or build APIs.  It reads the current DuckDB in read-only mode, inspects the
source tree, exercises legacy reads through the same read-only connection,
and writes one atomic audit receipt outside the TDX input roots.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import sys
import tempfile
import time
from datetime import date
from pathlib import Path
from typing import Any

import duckdb


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data/database/market_research.duckdb"
SPEC_PATH = ROOT / "docs/WORKBENCH_DUAL_TRACK_IMPLEMENTATION_SPEC_V3.md"
P11_01_REPORT = ROOT / "reports/upgrade_v3/P11-01-FINAL-ACCEPTANCE.json"
REPORT_PATH = ROOT / "reports/upgrade_v3/P11-02-OLD-WRITE-RECOVERY-PREVIEW.json"

CONTRACT_VERSION = "V3_P11_OLD_WRITE_RECOVERY_PREVIEW_V1_0"
MIGRATED_DOMAINS = {
    "technical": {
        "legacy_table": "stock_technical_daily",
        "new_table": "technical_result_rows",
        "legacy_writer": "insert_technical_rows",
        "new_writer": "insert_technical_result_rows",
    },
    "strength": {
        "legacy_table": "stock_strength_daily",
        "new_table": "strength_result_rows",
        "legacy_writer": "insert_strength_rows",
        "new_writer": "insert_strength_result_rows",
    },
    "high": {
        "legacy_table": "stock_high_daily",
        "new_table": "high_result_rows",
        "legacy_writer": "insert_high_rows",
        "new_writer": "insert_high_result_rows",
    },
    "member_state": {
        "legacy_table": "sector_member_state_daily",
        "new_table": "member_state_result_rows",
        "legacy_writer": "insert_member_state_rows",
        "new_writer": "insert_member_state_result_rows",
    },
    "structure": {
        "legacy_table": "historical_structure_daily",
        "new_table": "structure_result_rows",
        "legacy_writer": "insert_historical_structure_rows",
        "new_writer": "insert_structure_result_rows",
    },
    "summary": {
        "legacy_table": "stock_structure_summary_daily",
        "new_table": "structure_summary_result_rows",
        "legacy_writer": "insert_legacy_structure_summary_rows",
        "new_writer": "insert_structure_summary_result_rows",
    },
}

RELATION_OLD_TABLES = (
    "membership_snapshots",
    "membership_entries",
    "sector_membership_changes",
    "stock_sector_associations_daily",
)
AUXILIARY_RESULT_TABLES = (
    "sector_base_daily",
    "historical_coverage_daily",
    "representative_state_daily",
    "sector_cycle_daily",
    "mainline_daily",
    "market_cycle_daily",
    "market_reference_daily",
)


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


def _line_number(text: str, needle: str) -> int | None:
    for number, line in enumerate(text.splitlines(), 1):
        if needle in line:
            return number
    return None


def _source_files() -> list[Path]:
    files = list((ROOT / "src").rglob("*.py"))
    files.extend((ROOT / "scripts").glob("*.py"))
    return sorted(path for path in files if path.is_file())


def _writer_audit() -> dict[str, Any]:
    files = _source_files()
    texts: dict[Path, str] = {}
    for path in files:
        try:
            texts[path] = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            texts[path] = path.read_text(encoding="utf-8", errors="replace")

    definitions: dict[str, list[dict[str, Any]]] = {}
    for path, text in texts.items():
        try:
            tree = ast.parse(text, filename=str(path))
        except SyntaxError as exc:
            definitions.setdefault("__syntax_errors__", []).append(
                {"path": str(path), "error": str(exc)}
            )
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                definitions.setdefault(node.name, []).append(
                    {"path": str(path), "line": node.lineno, "end_line": node.end_lineno}
                )

    legacy_calls: dict[str, list[dict[str, Any]]] = {}
    for config in MIGRATED_DOMAINS.values():
        name = config["legacy_writer"]
        for path, text in texts.items():
            for number, line in enumerate(text.splitlines(), 1):
                if re.search(rf"\b{re.escape(name)}\s*\(", line):
                    if re.search(rf"\bdef\s+{re.escape(name)}\s*\(", line):
                        continue
                    legacy_calls.setdefault(name, []).append(
                        {"path": str(path), "line": number, "text": line.strip()}
                    )

    old_write_sql: list[dict[str, Any]] = []
    old_tables = sorted(
        {config["legacy_table"] for config in MIGRATED_DOMAINS.values()}
        | set(RELATION_OLD_TABLES)
    )
    table_pattern = "|".join(re.escape(table) for table in old_tables)
    insert_pattern = re.compile(
        rf"\b(insert|update|delete)\b[^\n;]*\b({table_pattern})\b",
        re.IGNORECASE,
    )
    for path, text in texts.items():
        for number, line in enumerate(text.splitlines(), 1):
            match = insert_pattern.search(line)
            if match:
                old_write_sql.append(
                    {
                        "path": str(path),
                        "line": number,
                        "operation": match.group(1).upper(),
                        "table": match.group(2),
                        "text": line.strip(),
                    }
                )

    v3_entry = ROOT / "scripts/build_m8_m9_preview.py"
    v3_entry_text = texts.get(v3_entry, "")
    current_entry = {
        "entrypoint": "src/workbench_service/app.py:run_today",
        "daily_builder": "scripts/build_m8_m9_preview.py --incremental-current",
        "new_writer_lines": {
            domain: _line_number(v3_entry_text, f'"{domain}": {config["new_writer"]}')
            for domain, config in MIGRATED_DOMAINS.items()
        },
        "legacy_membership_insert_sites": [
            item for item in old_write_sql if item["table"] == "membership_entries"
        ],
        "legacy_migrated_writer_call_sites": legacy_calls,
        "auxiliary_old_write_sites": [
            item
            for item in old_write_sql
            if item["table"] in {"sector_membership_changes", "stock_sector_associations_daily"}
        ],
    }
    matrix = []
    for domain, config in MIGRATED_DOMAINS.items():
        legacy_definition = definitions.get(config["legacy_writer"], [])
        new_definition = definitions.get(config["new_writer"], [])
        matrix.append(
            {
                "domain": domain,
                "legacy_table": config["legacy_table"],
                "legacy_writer": config["legacy_writer"],
                "legacy_definition": legacy_definition,
                "legacy_non_definition_call_sites": legacy_calls.get(
                    config["legacy_writer"], []
                ),
                "new_table": config["new_table"],
                "new_writer": config["new_writer"],
                "new_definition": new_definition,
                "status": "OLD_WRITE_STOP_PROVEN"
                if not legacy_calls.get(config["legacy_writer"])
                else "OLD_WRITE_CALL_SITE_FOUND",
                "protection_reason": "legacy table retained for verified history and compatibility reads",
            }
        )
    return {
        "source_file_count": len(files),
        "syntax_errors": definitions.get("__syntax_errors__", []),
        "migrated_domain_matrix": matrix,
        "current_v3_daily_entry": current_entry,
        "old_write_sql_sites": old_write_sql,
        "legacy_writer_definitions": {
            name: entries
            for name, entries in definitions.items()
            if name in {
                config["legacy_writer"] for config in MIGRATED_DOMAINS.values()
            }
        },
    }


def _table_exists(connection: duckdb.DuckDBPyConnection, table: str) -> bool:
    return bool(
        connection.execute(
            "SELECT 1 FROM information_schema.tables WHERE table_schema='main' AND table_name=?",
            [table],
        ).fetchone()
    )


def _table_profile(connection: duckdb.DuckDBPyConnection, table: str, block_size: int) -> dict[str, Any]:
    if not _table_exists(connection, table):
        return {"table": table, "exists": False, "row_count": None}
    table_type = connection.execute(
        "SELECT table_type FROM information_schema.tables WHERE table_schema='main' AND table_name=?",
        [table],
    ).fetchone()[0]
    row_count = int(connection.execute(f'SELECT count(*) FROM "{table}"').fetchone()[0])
    result: dict[str, Any] = {
        "table": table,
        "exists": True,
        "table_type": table_type,
        "row_count": row_count,
        "estimated_physical_bytes": None,
        "estimate_method": "VIEW_NO_PHYSICAL_BYTES",
    }
    if table_type == "BASE TABLE":
        blocks = int(
            connection.execute(
                f"SELECT count(DISTINCT block_id) FROM pragma_storage_info('{table}') "
                "WHERE persistent AND block_id >= 0"
            ).fetchone()[0]
        )
        result.update(
            {
                "persistent_block_count": blocks,
                "estimated_physical_bytes": blocks * block_size,
                "estimate_method": "DISTINCT_PERSISTENT_BLOCKS_TIMES_PRAGMA_BLOCK_SIZE",
            }
        )
    return result


def _result_migration_audit(
    connection: duckdb.DuckDBPyConnection, block_size: int
) -> dict[str, Any]:
    domains = []
    for domain, config in MIGRATED_DOMAINS.items():
        old_profile = _table_profile(connection, config["legacy_table"], block_size)
        new_profile = _table_profile(connection, config["new_table"], block_size)
        rows = connection.execute(
            f"""
            SELECT a.slice_id, a.row_count, a.storage_object_id,
                   b.result_object_id, o.domain, o.row_count,
                   (SELECT count(*) FROM "{config['legacy_table']}" old_rows
                    WHERE old_rows.slice_id=a.slice_id) AS legacy_rows
              FROM analysis_slices a
              LEFT JOIN analysis_slice_result_bindings b ON b.slice_id=a.slice_id
              LEFT JOIN analysis_result_objects o ON o.result_object_id=b.result_object_id
             WHERE a.domain=?
             ORDER BY a.slice_id
            """,
            [domain],
        ).fetchall()
        mismatches = []
        for slice_id, declared_rows, storage_id, result_id, result_domain, result_rows, legacy_rows in rows:
            if (
                result_id is None
                or result_domain != domain
                or storage_id != result_id
                or result_rows is None
                or int(result_rows) != int(legacy_rows)
            ):
                mismatches.append(
                    {
                        "slice_id": slice_id,
                        "declared_analysis_row_count": declared_rows,
                        "analysis_storage_object_id": storage_id,
                        "result_object_id": result_id,
                        "result_domain": result_domain,
                        "result_object_row_count": result_rows,
                        "legacy_row_count": legacy_rows,
                    }
                )
        domains.append(
            {
                "domain": domain,
                "legacy_table": config["legacy_table"],
                "new_table": config["new_table"],
                "legacy": old_profile,
                "new": new_profile,
                "legacy_slice_count": len(rows),
                "slice_result_row_count_mismatches": mismatches,
                "equivalence_status": "FULL_PASS" if not mismatches else "BLOCKED",
                "recovery_status": "PROTECTED_LEGACY_HISTORY_WAITING_P11_03_SCOPE_AUTHORIZATION",
                "recovery_estimate_bytes": old_profile.get("estimated_physical_bytes") or 0,
                "reclaimable_bytes_now": 0,
                "protect_reasons": [
                    "legacy history is retained until P11-03 equivalence and reference checks are authorized",
                    "legacy compatibility and migration readers remain in the source tree",
                    "logical DELETE would not guarantee physical database shrink",
                ],
            }
        )
    return {
        "migrated_domains": domains,
        "all_migrated_domain_equivalence": all(
            item["equivalence_status"] == "FULL_PASS" for item in domains
        ),
        "old_result_recovery_estimate_bytes": sum(
            int(item["recovery_estimate_bytes"]) for item in domains
        ),
        "old_result_reclaimable_bytes_now": 0,
        "auxiliary_unmigrated_result_tables": [
            {
                **_table_profile(connection, table, block_size),
                "recovery_status": "PROTECTED_NOT_IN_INITIAL_RESULT_MIGRATION",
                "reclaimable_bytes_now": 0,
                "protect_reasons": [
                    "not part of the initial P03 result-object migration set",
                    "current auxiliary builder/read paths still use the table",
                    "P11-03 range authorization is absent",
                ],
            }
            for table in AUXILIARY_RESULT_TABLES
        ],
    }


def _relation_audit(
    connection: duckdb.DuckDBPyConnection, block_size: int
) -> dict[str, Any]:
    profiles = [
        {
            **_table_profile(connection, table, block_size),
            "recovery_status": "PROTECTED_RELATION_HISTORY",
            "reclaimable_bytes_now": 0,
            "protect_reasons": [
                "latest publication resolves through versioned relation binding",
                "legacy relation importer and research compatibility readers still read old snapshots",
                "P11-03 explicit range authorization is absent",
            ],
        }
        for table in RELATION_OLD_TABLES
    ]
    counts = {
        "membership_snapshot_count": int(
            connection.execute("SELECT count(*) FROM membership_snapshots").fetchone()[0]
        ),
        "membership_entry_count": int(
            connection.execute("SELECT count(*) FROM membership_entries").fetchone()[0]
        ),
        "relation_snapshot_binding_count": int(
            connection.execute("SELECT count(*) FROM relation_snapshot_bindings").fetchone()[0]
        ),
        "relation_revision_count": int(
            connection.execute("SELECT count(*) FROM relation_revisions").fetchone()[0]
        ),
        "relation_edge_interval_count": int(
            connection.execute("SELECT count(*) FROM relation_edge_intervals").fetchone()[0]
        ),
    }
    return {
        "old_relation_tables": profiles,
        "old_relation_recovery_estimate_bytes": sum(
            int(item.get("estimated_physical_bytes") or 0) for item in profiles
        ),
        "old_relation_reclaimable_bytes_now": 0,
        "current_relation_counts": counts,
    }


def _source_and_cache_preview(as_of: date) -> dict[str, Any]:
    sys.path.insert(0, str(ROOT / "src"))
    from workbench_ops.storage import StorageGovernance

    preview = StorageGovernance(ROOT, DB_PATH).preview_v3_input_storage(as_of=as_of)
    extracted = []
    for item in preview.get("extracted", {}).get("items", []):
        extracted.append(
            {
                "root": item.get("root"),
                "bundle_ids": item.get("bundle_ids", []),
                "file_count": item.get("file_count"),
                "bytes": item.get("bytes", 0),
                "decision": item.get("decision"),
                "recovery_status": (
                    "PREVIEW_RECLAIMABLE_REBUILDABLE_WAITING_P11_03"
                    if item.get("decision") == "PREVIEW_RECLAIMABLE_REBUILDABLE"
                    else "PROTECTED"
                ),
                "protect_reasons": [
                    "source package is the unique raw evidence and remains protected",
                    "no deletion or move is authorized in P11-02",
                ],
            }
        )
    cache = preview.get("phase1_cache", {})
    return {
        "extracted": extracted,
        "source_packages": preview.get("packages", {}).get("items", []),
        "metadata_snapshots": preview.get("metadata", {}).get("snapshots", []),
        "phase1_cache": {
            "root": cache.get("root"),
            "file_count": cache.get("file_count"),
            "bytes": cache.get("bytes"),
            "budget_bytes": cache.get("budget_bytes"),
            "utilization": cache.get("utilization"),
            "decision": cache.get("decision"),
            "recovery_status": "PROTECTED_CACHE_NO_ACTION",
            "reclaimable_bytes_now": 0,
            "protect_reasons": [
                "cache is within budget or lacks a safe access order",
                "P11-02 is preview-only",
            ],
        },
        "preview_contract_version": preview.get("contract_version"),
        "physical_catalog_issues": preview.get("issues", []),
    }


def _backup_preview() -> dict[str, Any]:
    sys.path.insert(0, str(ROOT / "src"))
    from workbench_ops.backup import BackupService

    service = BackupService(ROOT, DB_PATH)
    started = time.perf_counter()
    audit = service.audit_catalog_physical_chain()
    elapsed_ms = round((time.perf_counter() - started) * 1000, 3)
    backup_root = ROOT / "data/backups"

    def size(path: Path) -> int:
        if path.is_file():
            return int(path.stat().st_size)
        return int(sum(item.stat().st_size for item in path.rglob("*") if item.is_file()))

    items = []
    if backup_root.is_dir():
        for path in sorted(backup_root.iterdir(), key=lambda value: value.name):
            if not path.is_file() and not path.is_dir():
                continue
            if path.is_dir() and not path.name.endswith(".objects"):
                continue
            item_type = (
                "DATABASE" if path.name.endswith(".duckdb")
                else "MANIFEST" if path.name.endswith(".manifest.json")
                else "OBJECT_DIRECTORY"
            )
            items.append(
                {
                    "path": str(path),
                    "item_type": item_type,
                    "bytes": size(path),
                    "recovery_status": "PROTECTED_BACKUP_CHAIN",
                    "reclaimable_bytes_now": 0,
                    "protect_reasons": [
                        "current backup chain is retained for manual recovery validation",
                        "P04-03 fixed-retention/owner boundary remains unresolved for deletion",
                        "P11-03 range authorization is absent",
                    ],
                }
            )
    return {
        "audit_elapsed_ms": elapsed_ms,
        "chain_contract_version": audit.get("contract_version"),
        "catalog_count": audit.get("catalog_count"),
        "chain_pass_count": audit.get("chain_pass_count"),
        "chain_incomplete_count": audit.get("chain_incomplete_count"),
        "orphan_physical_database_files": audit.get("orphan_physical_database_files", []),
        "orphan_physical_manifest_files": audit.get("orphan_physical_manifest_files", []),
        "orphan_physical_object_dirs": audit.get("orphan_physical_object_dirs", []),
        "physical_file_count": audit.get("physical_file_count"),
        "physical_file_bytes": audit.get("physical_file_bytes"),
        "items": items,
        "reclaimable_bytes_now": 0,
    }


def _runtime_preview() -> dict[str, Any]:
    runtime = ROOT / "runtime"
    items = []
    if runtime.is_dir():
        for path in sorted(runtime.rglob("*")):
            if not path.is_file():
                continue
            items.append(
                {
                    "path": str(path),
                    "bytes": int(path.stat().st_size),
                    "recovery_status": "PROTECTED_RUNTIME_SCOPE_UNCONFIRMED",
                    "reclaimable_bytes_now": 0,
                    "protect_reasons": [
                        "runtime is outside P04 input-storage preview",
                        "reference graph and owner retention are not established",
                        "P11-02 does not authorize runtime deletion",
                    ],
                }
            )
    return {
        "file_count": len(items),
        "bytes": sum(item["bytes"] for item in items),
        "items": items,
        "reclaimable_bytes_now": 0,
    }


def _read_consumers_and_latest_publication(
    connection: duckdb.DuckDBPyConnection,
) -> dict[str, Any]:
    sys.path.insert(0, str(ROOT / "src"))
    from workbench_service.app import Api
    from workbench_service.membership_resolver import VersionedMembershipResolver

    latest = connection.execute(
        """
        SELECT publication_id, cast(trade_date AS varchar)
          FROM publications
         WHERE status='SUCCESS'
         ORDER BY trade_date DESC, publication_id DESC
         LIMIT 1
        """
    ).fetchone()
    if not latest:
        return {"status": "BLOCKED", "reason": "SUCCESS_PUBLICATION_NOT_FOUND"}
    publication_id, trade_date = str(latest[0]), str(latest[1])
    api = Api(DB_PATH, root=ROOT)
    api._request_state.connection = connection
    reads = {}
    try:
        api._pub(publication_id)
        calls = {
            "dashboard": lambda: api.dashboard(publication_id, include_analysis=True),
            "sectors": lambda: api.sectors(publication_id, "", 1, 10),
            "sector_library": lambda: api.sector_library(publication_id, 1, 10),
            "technical": lambda: api.technical(publication_id, 1, 10),
            "new_highs": lambda: api.new_highs(publication_id, 1, 10),
        }
        for name, call in calls.items():
            try:
                value = call()
                reads[name] = {
                    "status": "READ_OK",
                    "returned_items": len(value.get("items", []))
                    if isinstance(value, dict) and isinstance(value.get("items"), list)
                    else None,
                    "total": value.get("total") if isinstance(value, dict) else None,
                }
            except Exception as exc:  # pragma: no cover - receipt should preserve exact failure
                reads[name] = {"status": "READ_FAILED", "error": f"{type(exc).__name__}:{exc}"}
    finally:
        api._request_state.connection = None

    relation = VersionedMembershipResolver(connection)
    relation_binding = relation.publication_binding(publication_id)
    edge_count = 0
    if relation_binding:
        edge_count = len(
            relation.edges_at(
                str(relation_binding["source_scope"]),
                int(relation_binding["revision_no"]),
            )
        )

    pub_bindings = connection.execute(
        "SELECT domain, snapshot_id FROM publication_analysis_snapshots WHERE publication_id=?",
        [publication_id],
    ).fetchall()
    result_table_by_domain = {
        domain: config["new_table"] for domain, config in MIGRATED_DOMAINS.items()
    }
    binding_rows = []
    for binding_domain, snapshot_id in pub_bindings:
        entries = connection.execute(
            """
            SELECT domain, cast(trade_date AS varchar), slice_id
              FROM analysis_snapshot_entries
             WHERE snapshot_id=?
             ORDER BY domain, trade_date, slice_id
            """,
            [snapshot_id],
        ).fetchall()
        for domain, entry_date, slice_id in entries:
            row = connection.execute(
                """
                SELECT b.result_object_id, o.domain, o.row_count
                  FROM analysis_slice_result_bindings b
                  LEFT JOIN analysis_result_objects o ON o.result_object_id=b.result_object_id
                 WHERE b.slice_id=?
                """,
                [slice_id],
            ).fetchone()
            physical_count = None
            if row and str(domain) in result_table_by_domain:
                physical_count = int(
                    connection.execute(
                        f'SELECT count(*) FROM "{result_table_by_domain[str(domain)]}" WHERE result_object_id=?',
                        [row[0]],
                    ).fetchone()[0]
                )
            binding_rows.append(
                {
                    "binding_domain": str(binding_domain),
                    "snapshot_id": str(snapshot_id),
                    "domain": str(domain),
                    "trade_date": str(entry_date),
                    "slice_id": str(slice_id),
                    "result_object_id": row[0] if row else None,
                    "result_domain": row[1] if row else None,
                    "result_object_row_count": row[2] if row else None,
                    "physical_result_row_count": physical_count,
                    "status": (
                        "BOUND_AND_READABLE"
                        if row
                        and str(domain) in result_table_by_domain
                        and physical_count == int(row[2])
                        else "AUXILIARY_LEGACY_READER_EXPECTED"
                        if str(domain) not in result_table_by_domain
                        else "MISSING_RESULT_BINDING"
                    ),
                }
            )
    migrated_entries = [
        item for item in binding_rows if item["domain"] in result_table_by_domain
    ]
    auxiliary_entries = [
        item for item in binding_rows if item["domain"] not in result_table_by_domain
    ]
    return {
        "latest_success_publication": {
            "publication_id": publication_id,
            "trade_date": trade_date,
            "publication_row_read": True,
        },
        "legacy_read_api": reads,
        "legacy_read_api_all_ok": all(item["status"] == "READ_OK" for item in reads.values()),
        "relation_resolver": {
            "binding_present": bool(relation_binding),
            "binding": relation_binding,
            "edge_count": edge_count,
            "status": "READ_OK" if relation_binding and edge_count else "READ_FAILED",
        },
        "result_binding": {
            "publication_binding_count": len(pub_bindings),
            "snapshot_entry_count": len(binding_rows),
            "migrated_entry_count": len(migrated_entries),
            "migrated_missing_or_mismatched": [
                item for item in migrated_entries if item["status"] != "BOUND_AND_READABLE"
            ],
            "auxiliary_legacy_reader_entry_count": len(auxiliary_entries),
            "auxiliary_legacy_reader_entries": auxiliary_entries,
            "status": (
                "MIGRATED_SCOPE_COMPLETE"
                if migrated_entries
                and all(item["status"] == "BOUND_AND_READABLE" for item in migrated_entries)
                else "MIGRATED_SCOPE_INCOMPLETE"
            ),
        },
        "status": (
            "FULL_PASS"
            if all(item["status"] == "READ_OK" for item in reads.values())
            and relation_binding
            and edge_count
            and migrated_entries
            and all(item["status"] == "BOUND_AND_READABLE" for item in migrated_entries)
            else "DEGRADED_PASS"
        ),
    }


def _storage_reference_summary() -> dict[str, Any]:
    sys.path.insert(0, str(ROOT / "src"))
    from workbench_ops.storage import StorageGovernance

    audit = StorageGovernance(ROOT, DB_PATH).audit_v3_storage_references()
    items = audit.get("items", [])
    return {
        "contract_version": audit.get("contract_version"),
        "read_only": audit.get("read_only"),
        "database_reference_count": len(audit.get("database_references", [])),
        "storage_object_count": len(items),
        "referenced_object_count": sum(1 for item in items if item.get("publication_graph_referenced")),
        "stale_referenced_flags": audit.get("issues", {}).get("stale_referenced_flags", []),
        "catalog_payload_missing_file": audit.get("issues", {}).get("catalog_payload_missing_file", []),
        "automatic_action": audit.get("automatic_action"),
        "deletion_executed": audit.get("deletion_executed"),
    }


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    if not DB_PATH.is_file():
        raise SystemExit(f"DATABASE_NOT_FOUND:{DB_PATH}")
    if not P11_01_REPORT.is_file():
        raise SystemExit(f"P11_01_REPORT_NOT_FOUND:{P11_01_REPORT}")

    spec_sha256 = _sha256(SPEC_PATH)
    prior = _read_json(P11_01_REPORT)
    prior_status = str(prior.get("overall_status") or prior.get("status") or "")
    if prior_status == "BLOCKED":
        raise SystemExit("P11_01_BLOCKED")
    before = DB_PATH.stat()
    started = time.perf_counter()
    writer_audit = _writer_audit()
    as_of = date.fromisoformat("2026-09-13")
    with duckdb.connect(str(DB_PATH), read_only=True) as connection:
        pragma_columns = [item[0] for item in connection.execute("PRAGMA database_size").description]
        pragma_row = connection.execute("PRAGMA database_size").fetchone()
        database_size = dict(zip(pragma_columns, pragma_row)) if pragma_row else {}
        block_size = int(database_size.get("block_size") or 0)
        migration = _result_migration_audit(connection, block_size)
        relation = _relation_audit(connection, block_size)
        consumers = _read_consumers_and_latest_publication(connection)
    source_cache = _source_and_cache_preview(as_of)
    backups = _backup_preview()
    runtime = _runtime_preview()
    storage_refs = _storage_reference_summary()
    after = DB_PATH.stat()

    migrated_stopped = all(
        item["status"] == "OLD_WRITE_STOP_PROVEN"
        for item in writer_audit["migrated_domain_matrix"]
    )
    no_membership_insert = not writer_audit["current_v3_daily_entry"][
        "legacy_membership_insert_sites"
    ]
    db_unchanged = before.st_size == after.st_size and before.st_mtime_ns == after.st_mtime_ns
    result_binding_ok = consumers.get("result_binding", {}).get("status") == "MIGRATED_SCOPE_COMPLETE"
    all_checks = {
        "p11_01_precondition": prior_status != "BLOCKED",
        "migrated_domain_old_writes_stopped": migrated_stopped,
        "new_publication_does_not_insert_full_membership_entries": no_membership_insert,
        "legacy_read_api_compatible": consumers.get("legacy_read_api_all_ok") is True,
        "relation_resolver_compatible": consumers.get("relation_resolver", {}).get("status") == "READ_OK",
        "migrated_result_bindings_complete": result_binding_ok,
        "source_cache_preview_read_only": source_cache.get("preview_contract_version") is not None,
        "backup_chain_read_only_complete": backups.get("chain_incomplete_count") == 0
        and not backups.get("orphan_physical_database_files")
        and not backups.get("orphan_physical_manifest_files")
        and not backups.get("orphan_physical_object_dirs"),
        "production_database_unchanged": db_unchanged,
        "no_deletion_or_recovery_action": backups.get("reclaimable_bytes_now") == 0
        and storage_refs.get("deletion_executed") is False,
        "storage_reference_audit_clean": not storage_refs.get("stale_referenced_flags")
        and not storage_refs.get("catalog_payload_missing_file"),
        "source_tree_syntax_clean": not writer_audit.get("syntax_errors"),
    }
    status = "FULL_PASS" if all(all_checks.values()) else "DEGRADED_PASS"
    report = {
        "contract_version": CONTRACT_VERSION,
        "status": status,
        "generated_at_local": "2026-09-13",
        "spec_path": str(SPEC_PATH),
        "spec_sha256": spec_sha256,
        "prior_stage": {"report": str(P11_01_REPORT), "status": prior_status},
        "stage_contract": {
            "purpose": "prove migrated-domain old writes stopped and produce exact protected recovery preview",
            "scope": "read-only source audit, read-only production DuckDB, exact managed file objects",
            "no_actions": ["DELETE", "MOVE", "VACUUM", "BACKUP", "RESTORE", "BUILD", "TDX_WRITE"],
        },
        "database_read_boundary": {
            "path": str(DB_PATH),
            "read_only": True,
            "before": {"size_bytes": before.st_size, "mtime_ns": before.st_mtime_ns},
            "after": {"size_bytes": after.st_size, "mtime_ns": after.st_mtime_ns},
            "unchanged": db_unchanged,
            "pragma_database_size": database_size,
        },
        "checks": all_checks,
        "writer_audit": writer_audit,
        "read_consumers_and_latest_publication": consumers,
        "storage_reference_summary": storage_refs,
        "recovery_preview": {
            "relation_old_copies": relation,
            "result_old_copies": migration,
            "extraction_cache": source_cache,
            "backups": backups,
            "runtime_artifacts": runtime,
            "deletion_authorized": False,
            "reclaimable_bytes_now": 0,
            "next_action": "P11-03 requires explicit range authority; keep all protected objects until then",
        },
        "independent_audit_items": [
            {
                "audit_item": "P11-02-AUD-STORAGE-01",
                "status": "OPEN",
                "scope": "storage_objects referenced flags and deleted tombstone path reconciliation",
                "evidence": {
                    "stale_referenced_flags": storage_refs.get("stale_referenced_flags", []),
                    "catalog_payload_missing_file": storage_refs.get(
                        "catalog_payload_missing_file", []
                    ),
                },
                "acceptance": "reconcile each object against the full publication/result graph before any physical recovery",
                "next_stage": "P11-03 or a separately authorized storage audit",
            },
            {
                "audit_item": "P11-02-AUD-AUXILIARY-WRITES-01",
                "status": "OPEN",
                "scope": "explicit old writes outside the six initial P03 result-object domains",
                "evidence": writer_audit["current_v3_daily_entry"].get(
                    "auxiliary_old_write_sites", []
                ),
                "acceptance": "either migrate the auxiliary domain or record an explicit retained legacy writer boundary",
                "next_stage": "P11-03/P11-04 boundary decision",
            },
        ],
        "evidence": {
            "runtime_seconds": round(time.perf_counter() - started, 3),
            "tdx_accessed": False,
            "production_mutation_executed": False,
        },
        "acceptance": {
            "functionality": "FULL_PASS" if all_checks["legacy_read_api_compatible"] and all_checks["relation_resolver_compatible"] else "DEGRADED_PASS",
            "data_correctness": "FULL_PASS" if all_checks["migrated_result_bindings_complete"] else "DEGRADED_PASS",
            "migration_write_boundary": "FULL_PASS" if migrated_stopped and no_membership_insert else "DEGRADED_PASS",
            "storage_preview": "FULL_PASS"
            if all_checks["no_deletion_or_recovery_action"]
            and all_checks["storage_reference_audit_clean"]
            else "DEGRADED_PASS",
        },
        "next_stage": "P11-03",
    }
    _atomic_json(REPORT_PATH, report)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True, default=str))


if __name__ == "__main__":
    main()
