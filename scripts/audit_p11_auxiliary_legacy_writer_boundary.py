"""Audit the two intentionally retained auxiliary legacy writer boundaries.

This closes the P11-02 auxiliary-writer audit without migrating or deleting
the tables.  The audit is static plus read-only DuckDB inspection; it never
executes either writer or changes production state.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import tempfile
import time
from pathlib import Path
from typing import Any

import duckdb


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data/database/market_research.duckdb"
SPEC_PATH = ROOT / "docs/WORKBENCH_DUAL_TRACK_IMPLEMENTATION_SPEC_V3.md"
P11_02_REPORT = ROOT / "reports/upgrade_v3/P11-02-OLD-WRITE-RECOVERY-PREVIEW.json"
REPORT_PATH = ROOT / "reports/upgrade_v3/P11-02-AUD-AUXILIARY-WRITES-BOUNDARY-20260913.json"

CONTRACT_VERSION = "V3_P11_AUXILIARY_LEGACY_WRITER_BOUNDARY_V1_0"
TABLES = {
    "membership_changes": {
        "table": "sector_membership_changes",
        "writer": "insert_membership_change_rows",
        "path": ROOT / "src/workbench_analysis/member_state.py",
        "current_entry": ROOT / "scripts/build_m8_m9_preview.py",
    },
    "association": {
        "table": "stock_sector_associations_daily",
        "writer": "_insert_association_rows",
        "path": ROOT / "scripts/build_m11_association_preview.py",
        "current_entry": ROOT / "scripts/build_m11_association_preview.py",
    },
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


def _source_files() -> list[Path]:
    return sorted([*ROOT.joinpath("src").rglob("*.py"), *ROOT.joinpath("scripts").glob("*.py")])


def _ast_inventory() -> tuple[dict[Path, str], list[dict[str, Any]]]:
    texts: dict[Path, str] = {}
    syntax_errors: list[dict[str, Any]] = []
    for path in _source_files():
        text = path.read_text(encoding="utf-8", errors="replace")
        texts[path] = text
        try:
            ast.parse(text, filename=str(path))
        except SyntaxError as exc:
            syntax_errors.append({"path": str(path), "error": str(exc)})
    return texts, syntax_errors


def _line_hits(text: str, pattern: str) -> list[dict[str, Any]]:
    expression = re.compile(pattern, re.IGNORECASE)
    return [
        {"line": line_no, "text": line.strip()}
        for line_no, line in enumerate(text.splitlines(), 1)
        if expression.search(line)
    ]


def _call_sites(texts: dict[Path, str], function_name: str) -> list[dict[str, Any]]:
    sites: list[dict[str, Any]] = []
    for path, text in texts.items():
        try:
            tree = ast.parse(text, filename=str(path))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            called = None
            if isinstance(node.func, ast.Name):
                called = node.func.id
            elif isinstance(node.func, ast.Attribute):
                called = node.func.attr
            if called == function_name:
                sites.append({"path": str(path), "line": node.lineno})
    return sorted(sites, key=lambda item: (item["path"], item["line"]))


def _table_snapshot(connection: duckdb.DuckDBPyConnection, table: str) -> dict[str, Any]:
    quoted = '"' + table.replace('"', '""') + '"'
    row = connection.execute(
        f"select count(*), count(distinct slice_id), min(trade_date), max(trade_date) from {quoted}"
    ).fetchone()
    return {
        "table": table,
        "row_count": row[0],
        "slice_count": row[1],
        "min_trade_date": str(row[2]) if row[2] is not None else None,
        "max_trade_date": str(row[3]) if row[3] is not None else None,
    }


def main() -> int:
    started = time.perf_counter()
    prior = json.loads(P11_02_REPORT.read_text(encoding="utf-8"))
    texts, syntax_errors = _ast_inventory()
    app_text = texts.get(ROOT / "src/workbench_service/app.py", "")
    builder_text = texts.get(ROOT / "scripts/build_m8_m9_preview.py", "")
    association_text = texts.get(ROOT / "scripts/build_m11_association_preview.py", "")

    writer_audits: dict[str, dict[str, Any]] = {}
    for domain, config in TABLES.items():
        writer_text = texts[config["path"]]
        table = config["table"]
        insert_hits = _line_hits(writer_text, rf"\binsert\s+into\s+{re.escape(table)}\b")
        update_delete_hits = _line_hits(
            writer_text, rf"\b(update|delete|drop|truncate)\b[^\n;]*\b{re.escape(table)}\b"
        )
        calls = _call_sites(texts, config["writer"])
        boundary_sites = _line_hits(
            config["current_entry"].read_text(encoding="utf-8", errors="replace"),
            rf"[\"']membership_changes[\"']\s*:\s*{re.escape(config['writer'])}\b",
        ) if domain == "membership_changes" else []
        writer_audits[domain] = {
            "table": table,
            "writer": config["writer"],
            "definition_path": str(config["path"]),
            "insert_sql_sites": insert_hits,
            "update_delete_drop_truncate_sites": update_delete_hits,
            "all_call_sites": calls,
            "bounded_call_site_count": len(calls),
            "writer_binding_sites": boundary_sites,
            "writer_boundary": (
                "CURRENT_INCREMENTAL_BUILDER_ONLY"
                if domain == "membership_changes"
                else "MANUAL_M11_PREVIEW_ONLY"
            ),
            "idempotency_markers": {
                "membership_existing_slice_check": "where slice_id=?" in writer_text
                if domain == "membership_changes"
                else None,
                "immutable_conflict_guard": "immutable_slice_state" in writer_text
                if domain == "membership_changes"
                else None,
                "association_transaction": ("begin transaction" in writer_text and "commit" in writer_text)
                if domain == "association"
                else None,
                "association_snapshot_dedup": "select 1 from analysis_snapshots" in writer_text
                if domain == "association"
                else None,
            },
            "read_consumers": _line_hits(
                app_text, rf"\bfrom\s+{re.escape(table)}\b|\bjoin\s+{re.escape(table)}\b"
            ),
        }

    checks = {
        "source_tree_syntax_clean": not syntax_errors,
        "membership_writer_has_one_bounded_call_site": (
            len(writer_audits["membership_changes"]["writer_binding_sites"]) == 1
            and writer_audits["membership_changes"]["writer_binding_sites"][0]["line"] == 640
            and writer_audits["membership_changes"]["all_call_sites"] == []
        ),
        "association_writer_is_manual_only": (
            writer_audits["association"]["bounded_call_site_count"] == 1
            and writer_audits["association"]["all_call_sites"][0]["path"] == str(ROOT / "scripts/build_m11_association_preview.py")
        ),
        "no_auxiliary_update_delete_sql": all(
            not audit["update_delete_drop_truncate_sites"] for audit in writer_audits.values()
        ),
        "membership_writer_idempotent_boundary": all(
            value is True
            for value in (
                writer_audits["membership_changes"]["idempotency_markers"]["membership_existing_slice_check"],
                writer_audits["membership_changes"]["idempotency_markers"]["immutable_conflict_guard"],
            )
        ),
        "association_writer_transactional_boundary": all(
            value is True
            for value in (
                writer_audits["association"]["idempotency_markers"]["association_transaction"],
                writer_audits["association"]["idempotency_markers"]["association_snapshot_dedup"],
            )
        ),
        "current_daily_entry_excludes_manual_association_builder": (
            "build_m8_m9_preview.py" in app_text
            and "--incremental-current" in app_text
            and "build_m11_association_preview.py" not in app_text
            and "build_m11_association_preview.py" not in builder_text
        ),
        "association_table_has_legacy_read_consumer": bool(writer_audits["association"]["read_consumers"]),
        "p11_02_audit_precondition": prior.get("contract_version") == "V3_P11_OLD_WRITE_RECOVERY_PREVIEW_V1_0",
    }

    with duckdb.connect(str(DB_PATH), read_only=True) as connection:
        snapshots = {domain: _table_snapshot(connection, config["table"]) for domain, config in TABLES.items()}
    report = {
        "contract_version": CONTRACT_VERSION,
        "status": "FULL_PASS" if all(checks.values()) else "DEGRADED_PASS",
        "stage": "P11-02 independent audit follow-up",
        "audit_item": "P11-02-AUD-AUXILIARY-WRITES-01",
        "audit_disposition": "RESOLVED_WITH_BOUNDED_LEGACY_WRITER_BOUNDARY" if all(checks.values()) else "OPEN",
        "checks": checks,
        "writer_audits": writer_audits,
        "database_read_boundary": {
            "path": str(DB_PATH),
            "read_only": True,
            "table_snapshots": snapshots,
        },
        "source_tree_syntax_errors": syntax_errors,
        "prior_report": str(P11_02_REPORT),
        "spec_path": str(SPEC_PATH),
        "spec_sha256": _sha256(SPEC_PATH),
        "safety": {
            "production_mutation_executed": False,
            "tdx_accessed": False,
            "tdx_mutated": False,
            "legacy_tables_deleted": False,
            "writer_executed": False,
        },
        "retention_boundary": {
            "decision": "RETAIN_UNTIL_V3_AND_UI_MIGRATION_COMPLETE",
            "reason": "User-directed old-table retention; this audit closes only the writer-boundary question.",
            "table_cleanup": "NOT_IN_SCOPE",
        },
        "generated_at_local": "2026-09-13",
        "runtime_seconds": round(time.perf_counter() - started, 3),
        "next_stage": "P11-04",
        "next_stage_gate": "P11-01 storage stop-growth and P11-02-AUD-STORAGE-01 remain open gates; old tables remain retained.",
    }
    _atomic_json(REPORT_PATH, report)
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
