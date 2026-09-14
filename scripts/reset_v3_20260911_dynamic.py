"""One-time, guarded reset of the 2026-09-11 generated local production state.

Source bundles, normalized input staging, relation revisions/edges, sector
attributes, hierarchy and schema catalogs are deliberately retained.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from workbench_db import WorkbenchRepository


ROOT = Path(__file__).resolve().parents[1]
DATABASE = ROOT / "data/database/market_research.duckdb"
TARGET_DATE = "2026-09-11"
PRESERVE = (
    "relation_edge_intervals", "relation_observations", "relation_revisions",
    "sector_attribute_revision_bindings", "sector_attribute_revisions",
    "sector_attribute_versions", "sector_semantic_versions",
    "tdx_sector_hierarchy_nodes", "tdx_sector_hierarchy_versions",
    "metadata_snapshots", "source_bundles", "source_files", "source_packages",
    "schema_migrations", "schema_migration_checks",
    "config_versions", "data_sources", "limit_rule_versions", "sector_versions",
    "security_metadata_versions", "security_versions", "membership_entries",
    "membership_snapshot_metadata", "membership_snapshots", "relation_snapshot_bindings",
)
DYNAMIC = (
    "research_signal_outcomes", "research_shortlist", "research_sector_member_roles",
    "research_sector_signal_state", "research_sector_states", "research_stock_states",
    "research_runs", "analysis_slice_result_bindings",
    "technical_result_rows", "strength_result_rows", "high_result_rows",
    "structure_result_rows", "structure_summary_result_rows", "member_state_result_rows",
    "analysis_result_objects",
    "analysis_slice_dependencies", "analysis_daily_basis", "analysis_snapshot_audit_status", "analysis_snapshot_entries",
    "analysis_snapshot_hierarchy", "publication_analysis_snapshots",
    "sector_cycle_daily", "sector_base_daily", "sector_member_state_daily",
    "sector_membership_changes", "representative_state_daily", "mainline_daily",
    "historical_coverage_daily", "historical_structure_daily", "stock_high_daily",
    "stock_strength_daily", "stock_structure_summary_daily", "stock_technical_daily",
    "market_cycle_daily", "market_daily", "market_reference_daily", "universe_state_daily",
    "analysis_slices", "analysis_snapshots",
    "candidate_daily", "stock_daily", "sector_daily", "unified_board", "structure_details",
    "queue_memberships", "queue_rankings", "stock_sector_associations_daily",
    "limit_ladder_daily", "limit_promotion_daily", "m8c_rule_audit_events",
    "online_batches", "online_event_bundles", "online_event_header", "online_evidence",
    "online_fetch_runs", "online_payloads", "online_pool_entries", "online_quote_entries",
    "online_rank_entries", "online_security_map", "storage_objects", "publication_artifacts",
    "publication_heads", "relation_publication_bindings", "publication_memberships",
    "publications", "job_events", "job_attempts", "jobs", "observations", "outcomes",
    "state_transitions",
    "audit_receipts", "backup_catalog", "cleanup_jobs", "leases",
)
GENERATED = (
    "data/factors/factors_daily.parquet", "data/normalized/adjusted_daily.parquet",
    "data/market/market_regime_daily.parquet", "data/sectors/sector_factors_daily.parquet",
    "data/sectors/sector_membership_daily.parquet",
    "data/scanner/sector_scanner_daily.parquet", "data/scanner/stock_scanner_daily.parquet",
    "data/candidates/candidate_pool_daily.parquet",
    "data/shadow/v2/20260911", "reports/releases/20260911", "reports/revisions/20260911",
    "reports/workbench/20260911", "reports/shadow/v2/20260911",
    "reports/current/20260911.json", "reports/current/CURRENT_RELEASE.json",
    "reports/current/CURRENT_STATUS.md",
    "reports/v3/daily/2026-09-11.plan.json", "reports/v3/daily/2026-09-11.report.json",
)


def _inside_workspace(path: Path) -> Path:
    resolved = path.resolve()
    if not resolved.is_relative_to(ROOT.resolve()) or resolved == ROOT.resolve():
        raise RuntimeError(f"RESET_PATH_OUTSIDE_WORKSPACE:{resolved}")
    return resolved


def _counts(con: duckdb.DuckDBPyConnection, tables: tuple[str, ...]) -> dict[str, int]:
    return {name: int(con.execute(f'SELECT count(*) FROM "{name}"').fetchone()[0]) for name in tables}


def run(*, execute: bool) -> dict:
    with duckdb.connect(str(DATABASE), read_only=True) as con:
        present = {row[0] for row in con.execute(
            "select table_name from information_schema.tables where table_schema='main' and table_type='BASE TABLE'"
        ).fetchall()}
        uncovered = present - set(PRESERVE) - set(DYNAMIC)
        missing = set(DYNAMIC) - present
        if uncovered or missing:
            raise RuntimeError(f"RESET_TABLE_CLASSIFICATION_INCOMPLETE:uncovered={sorted(uncovered)},missing={sorted(missing)}")
        publications = con.execute("select publication_id,trade_date,status from publications").fetchall()
        if len(publications) != 1 or str(publications[0][1]) != TARGET_DATE or publications[0][2] != "SUCCESS":
            raise RuntimeError(f"RESET_PUBLICATION_GUARD:{publications}")
        before = {"preserved": _counts(con, PRESERVE), "dynamic": _counts(con, DYNAMIC)}
    targets = [str(_inside_workspace(ROOT / relative).relative_to(ROOT)) for relative in GENERATED if (ROOT / relative).exists()]
    receipt = {"contract": "V3_20260911_DYNAMIC_RESET_V1", "target_date": TARGET_DATE,
               "preserved_tables": before["preserved"], "dynamic_tables_before": before["dynamic"],
               "generated_targets": targets, "executed": False}
    if not execute:
        return receipt

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    quarantine = _inside_workspace(ROOT / "reports/reset_quarantine" / stamp)
    quarantine.mkdir(parents=True, exist_ok=False)
    shutil.copy2(DATABASE, quarantine / DATABASE.name)
    moved = []
    try:
        for relative in targets:
            source = _inside_workspace(ROOT / relative)
            destination = _inside_workspace(quarantine / relative)
            destination.parent.mkdir(parents=True, exist_ok=True)
            source.rename(destination)
            moved.append((source, destination))
        DATABASE.unlink()
        with WorkbenchRepository(ROOT, DATABASE):
            pass
        with duckdb.connect(str(DATABASE)) as schema_connection:
            schema_connection.execute((ROOT / "src/workbench_db/research_runs_schema.sql").read_text(encoding="utf-8"))
        copy_order = (
            "source_packages", "source_bundles", "source_files", "metadata_snapshots",
            "tdx_sector_hierarchy_versions", "tdx_sector_hierarchy_nodes",
            "sector_attribute_revisions", "sector_attribute_versions", "sector_attribute_revision_bindings",
            "relation_revisions", "relation_observations", "relation_edge_intervals",
            "sector_semantic_versions", "membership_snapshots", "membership_entries",
            "membership_snapshot_metadata", "relation_snapshot_bindings",
            "config_versions", "data_sources", "limit_rule_versions", "sector_versions",
            "security_metadata_versions", "security_versions",
        )
        with duckdb.connect(str(DATABASE)) as con:
            con.execute(f"ATTACH '{(quarantine / DATABASE.name).as_posix()}' AS preserved (READ_ONLY)")
            for table in copy_order:
                con.execute(f'INSERT OR IGNORE INTO "{table}" SELECT * FROM preserved."{table}"')
            con.execute("DETACH preserved")
            after = {"preserved": _counts(con, PRESERVE), "dynamic": _counts(con, DYNAMIC)}
        if after["preserved"] != before["preserved"] or any(after["dynamic"].values()):
            raise RuntimeError("RESET_POSTCONDITION_FAILED")
        receipt.update({"executed": True, "quarantine": str(quarantine),
                        "dynamic_tables_after": after["dynamic"], "preserved_tables_after": after["preserved"]})
        (quarantine / "reset_receipt.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
        return receipt
    except Exception:
        shutil.copy2(quarantine / DATABASE.name, DATABASE)
        for source, destination in reversed(moved):
            if destination.exists():
                source.parent.mkdir(parents=True, exist_ok=True)
                destination.rename(source)
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    print(json.dumps(run(execute=args.execute), ensure_ascii=False, indent=2))
