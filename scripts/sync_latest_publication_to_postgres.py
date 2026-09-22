"""Synchronize the latest generated publication into the formal PostgreSQL schema.

This is deliberately narrower than the historical DuckDB migration: it copies one
new publication and the analysis snapshot bound to it, in one PostgreSQL
transaction.  The application is not switched by this script.  A failed copy is
rolled back, so a partial publication cannot become visible through PG.
"""
from __future__ import annotations

import argparse
import json
import os
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import duckdb
import psycopg
from psycopg import sql

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DUCKDB = ROOT / "data" / "database" / "market_research.duckdb"
DEFAULT_DSN = "host=127.0.0.1 port=5432 dbname=market_research user=postgres"
RELATION_SCOPE = "TDX-MEMBERSHIP:direct-members-v3-v1"


def qi(value: str) -> sql.Identifier:
    return sql.Identifier(value)


def dq(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def json_safe(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, allow_nan=False, default=str, separators=(",", ":"))
    # DuckDB returns JSON columns as strings.  PostgreSQL rejects NaN/Infinity.
    if isinstance(value, str):
        try:
            parsed = json.loads(value, parse_constant=lambda _: None)
            return json.dumps(parsed, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
        except json.JSONDecodeError:
            return value
    return value


def source_columns(duck: duckdb.DuckDBPyConnection, table: str) -> list[tuple[str, str]]:
    return [(str(r[0]), str(r[1])) for r in duck.execute(
        "select column_name, data_type from information_schema.columns "
        "where table_schema='main' and table_name=? order by ordinal_position", [table]
    ).fetchall()]


def target_columns(pg: psycopg.Connection[Any], table: str) -> list[tuple[str, str]]:
    with pg.cursor() as cur:
        cur.execute("select column_name,data_type from information_schema.columns "
                    "where table_schema='workbench' and table_name=%s order by ordinal_position", (table,))
        return [(str(r[0]), str(r[1])) for r in cur.fetchall()]


def source_tables(duck: duckdb.DuckDBPyConnection) -> set[str]:
    return {str(r[0]) for r in duck.execute(
        "select table_name from information_schema.tables where table_schema='main' and table_type='BASE TABLE'"
    ).fetchall()}


def target_tables(pg: psycopg.Connection[Any]) -> set[str]:
    with pg.cursor() as cur:
        cur.execute("select table_name from information_schema.tables where table_schema='workbench' and table_type='BASE TABLE'")
        return {str(r[0]) for r in cur.fetchall()}


def fetch_rows(duck: duckdb.DuckDBPyConnection, table: str, columns: list[str], predicate: str, params: list[Any]) -> list[tuple[Any, ...]]:
    projection = ",".join(dq(c) for c in columns)
    return duck.execute(f"select {projection} from main.{dq(table)}" + (f" where {predicate}" if predicate else ""), params).fetchall()


def copy_rows(
    duck: duckdb.DuckDBPyConnection,
    pg: psycopg.Connection[Any],
    table: str,
    predicate: str,
    params: list[Any],
    report: dict[str, int],
    upsert_head: bool = False,
) -> int:
    src = dict(source_columns(duck, table))
    tgt = target_columns(pg, table)
    if not tgt:
        return 0
    missing = [name for name, _ in tgt if name not in src]
    if missing:
        raise RuntimeError(f"{table}: target columns absent in DuckDB: {missing}")
    names = [name for name, _ in tgt]
    rows = fetch_rows(duck, table, names, predicate, params)
    if not rows:
        report[table] = 0
        return 0
    placeholders = []
    for _, typ in tgt:
        placeholders.append("%s::jsonb" if typ in ("json", "jsonb") else "%s")
    insert = sql.SQL("insert into workbench.{} ({}) values ({})").format(
        qi(table), sql.SQL(",").join(qi(n) for n in names), sql.SQL(",").join(sql.SQL(p) for p in placeholders)
    )
    if upsert_head:
        insert += sql.SQL(" on conflict (trade_date) do update set publication_id=excluded.publication_id")
    else:
        insert += sql.SQL(" on conflict do nothing")
    normalized = []
    for row in rows:
        normalized.append(tuple(json_safe(v) if typ in ("json", "jsonb") else v for v, (_, typ) in zip(row, tgt)))
    with pg.cursor() as cur:
        cur.executemany(insert, normalized)
    report[table] = len(rows)
    return len(rows)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--database", type=Path, default=DEFAULT_DUCKDB)
    p.add_argument("--dsn", default=None)
    p.add_argument("--trade-date", default=None, help="defaults to latest DuckDB publication head")
    p.add_argument("--report", type=Path, default=ROOT / "runtime/postgres_migration/20260922/pg_latest_publication_sync_report.json")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    duck = duckdb.connect(str(args.database.resolve()), read_only=True)
    report: dict[str, Any] = {
        "stage": "latest-publication-pg-sync",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "database": str(args.database.resolve()),
        "online_switch_performed": False,
        "data_generation_triggered": False,
        "status": "BLOCKED",
        "tables": {},
    }
    pg: psycopg.Connection[Any] | None = None
    try:
        pub = duck.execute("select publication_id,trade_date from publication_heads order by trade_date desc limit 1").fetchone()
        if not pub:
            raise RuntimeError("DuckDB has no publication head")
        publication_id, trade_date = str(pub[0]), pub[1]
        if args.trade_date:
            wanted = date.fromisoformat(args.trade_date)
            row = duck.execute("select publication_id,trade_date from publication_heads where trade_date=?", [wanted]).fetchone()
            if not row:
                raise RuntimeError(f"DuckDB has no publication for {wanted}")
            publication_id, trade_date = str(row[0]), row[1]
        snap_row = duck.execute("select snapshot_id from publication_analysis_snapshots where publication_id=? and domain='LOCAL_RECONSTRUCTED'", [publication_id]).fetchone()
        snapshot_id = str(snap_row[0]) if snap_row else None
        # Publication schema stores the bundle identity in source_path (there is
        # no source_bundle_id column on publications in this version).
        source_path_row = duck.execute("select source_path from publications where publication_id=?", [publication_id]).fetchone()
        bundle_id = Path(str(source_path_row[0])).name if source_path_row and source_path_row[0] else None
        report.update({"publication_id": publication_id, "trade_date": str(trade_date), "snapshot_id": snapshot_id, "source_bundle_id": bundle_id})
        if not snapshot_id:
            raise RuntimeError("latest publication has no LOCAL_RECONSTRUCTED analysis snapshot")

        selected = {str(r[0]) for r in duck.execute("select slice_id from analysis_snapshot_entries where snapshot_id=?", [snapshot_id]).fetchall()}
        objects = {str(r[0]) for r in duck.execute("select result_object_id from analysis_slice_result_bindings where slice_id in (select slice_id from analysis_snapshot_entries where snapshot_id=?)", [snapshot_id]).fetchall()}
        report["analysis_slice_count"] = len(selected)
        report["analysis_result_object_count"] = len(objects)
        pg = psycopg.connect(args.dsn or os.environ.get("PG_DSN") or DEFAULT_DSN)
        pg.autocommit = False
        src_tables = source_tables(duck)
        dst_tables = target_tables(pg)
        for required in ("publications", "publication_heads"):
            if required not in src_tables or required not in dst_tables:
                raise RuntimeError(f"required table missing: {required}")

        # Parent publication and its immutable publication rows.
        if bundle_id and "source_bundles" in src_tables and "source_bundles" in dst_tables:
            copy_rows(duck, pg, "source_bundles", "source_bundle_id=?", [bundle_id], report["tables"])
        copy_rows(duck, pg, "publications", "publication_id=?", [publication_id], report["tables"])

        publication_children = [
            "stock_daily", "sector_daily", "candidate_daily", "market_daily", "structure_details",
            "queue_memberships", "unified_board", "queue_rankings", "publication_artifacts", "publication_memberships",
        ]
        for table in publication_children:
            if table in src_tables and table in dst_tables:
                copy_rows(duck, pg, table, "publication_id=?", [publication_id], report["tables"])

        # Relation/attribute observation bound to today's publication.
        for table in ("relation_revisions", "relation_edge_intervals", "relation_observations", "sector_attribute_revisions", "sector_attribute_versions", "sector_attribute_revision_bindings"):
            if table in src_tables and table in dst_tables:
                copy_rows(duck, pg, table, "source_scope=?", [RELATION_SCOPE], report["tables"])
        if "relation_publication_bindings" in src_tables and "relation_publication_bindings" in dst_tables:
            copy_rows(duck, pg, "relation_publication_bindings", "publication_id=?", [publication_id], report["tables"])

        # Snapshot metadata and all slices/results referenced by the new snapshot.
        if "analysis_snapshots" in src_tables and "analysis_snapshots" in dst_tables:
            copy_rows(duck, pg, "analysis_snapshots", "snapshot_id=?", [snapshot_id], report["tables"])
        if "analysis_slices" in src_tables and "analysis_slices" in dst_tables:
            copy_rows(duck, pg, "analysis_slices", "slice_id in (select slice_id from analysis_snapshot_entries where snapshot_id=?)", [snapshot_id], report["tables"])
        if "analysis_daily_basis" in src_tables and "analysis_daily_basis" in dst_tables:
            copy_rows(duck, pg, "analysis_daily_basis", "slice_id in (select slice_id from analysis_snapshot_entries where snapshot_id=?)", [snapshot_id], report["tables"])
        for table in ("analysis_snapshot_hierarchy", "analysis_snapshot_audit_status"):
            if table in src_tables and table in dst_tables:
                copy_rows(duck, pg, table, "snapshot_id=?", [snapshot_id], report["tables"])
        if "analysis_slice_dependencies" in src_tables and "analysis_slice_dependencies" in dst_tables:
            copy_rows(duck, pg, "analysis_slice_dependencies", "slice_id in (select slice_id from analysis_snapshot_entries where snapshot_id=?)", [snapshot_id], report["tables"])
        if "analysis_result_objects" in src_tables and "analysis_result_objects" in dst_tables and objects:
            copy_rows(duck, pg, "analysis_result_objects", "result_object_id in (select result_object_id from analysis_slice_result_bindings where slice_id in (select slice_id from analysis_snapshot_entries where snapshot_id=?))", [snapshot_id], report["tables"])
        if "analysis_slice_result_bindings" in src_tables and "analysis_slice_result_bindings" in dst_tables:
            copy_rows(duck, pg, "analysis_slice_result_bindings", "slice_id in (select slice_id from analysis_snapshot_entries where snapshot_id=?)", [snapshot_id], report["tables"])

        # Every analysis result table is keyed by either slice_id or result_object_id.
        for table in sorted(src_tables & dst_tables):
            if table in report["tables"] or table.startswith("analysis_snapshot") or table in ("analysis_slices", "analysis_daily_basis", "analysis_slice_dependencies", "analysis_slice_result_bindings", "analysis_result_objects"):
                continue
            cols = {c for c, _ in source_columns(duck, table)}
            if "slice_id" in cols:
                copy_rows(duck, pg, table, "slice_id in (select slice_id from analysis_snapshot_entries where snapshot_id=?)", [snapshot_id], report["tables"])
            elif "result_object_id" in cols and objects:
                copy_rows(duck, pg, table, "result_object_id in (select result_object_id from analysis_slice_result_bindings where slice_id in (select slice_id from analysis_snapshot_entries where snapshot_id=?))", [snapshot_id], report["tables"])
        if "storage_objects" in src_tables and "storage_objects" in dst_tables:
            copy_rows(duck, pg, "storage_objects", "storage_object_id in (select storage_object_id from analysis_slices where slice_id in (select slice_id from analysis_snapshot_entries where snapshot_id=?))", [snapshot_id], report["tables"])
        if "analysis_snapshot_entries" in src_tables and "analysis_snapshot_entries" in dst_tables:
            copy_rows(duck, pg, "analysis_snapshot_entries", "snapshot_id=?", [snapshot_id], report["tables"])
        copy_rows(duck, pg, "publication_analysis_snapshots", "publication_id=? and domain='LOCAL_RECONSTRUCTED'", [publication_id], report["tables"])
        # Research registries are keyed by the publication/run generated for
        # this day.  Copy the parent run first, then its state/shortlist rows;
        # this keeps the PG research read model current without copying older
        # runs or mutable working data.
        research_run = duck.execute("select run_id from research_runs where publication_id=? order by created_at desc limit 1", [publication_id]).fetchone() if "research_runs" in src_tables else None
        if research_run and "research_runs" in dst_tables:
            run_id = str(research_run[0])
            copy_rows(duck, pg, "research_runs", "run_id=?", [run_id], report["tables"])
            for table in sorted(src_tables & dst_tables):
                if table in report["tables"] or table in {"research_runs", "research_runs_v3_3"}:
                    continue
                cols = {c for c, _ in source_columns(duck, table)}
                if "run_id" in cols:
                    copy_rows(duck, pg, table, "run_id=?", [run_id], report["tables"])
                elif "signal_run_id" in cols:
                    copy_rows(duck, pg, table, "signal_run_id=?", [run_id], report["tables"])
        if "research_runs_v3_3" in src_tables and "research_runs_v3_3" in dst_tables:
            copy_rows(duck, pg, "research_runs_v3_3", "publication_id=?", [publication_id], report["tables"])
            bundle = duck.execute("select bundle_digest from research_runs_v3_3 where publication_id=? order by registered_at desc limit 1", [publication_id]).fetchone()
            if bundle and "research_candidates_v3_3" in src_tables and "research_candidates_v3_3" in dst_tables:
                copy_rows(duck, pg, "research_candidates_v3_3", "bundle_digest=?", [str(bundle[0])], report["tables"])
        copy_rows(duck, pg, "publication_heads", "trade_date=?", [trade_date], report["tables"], upsert_head=True)

        # Hard verification runs before commit; rollback on any mismatch.
        with pg.cursor() as cur:
            cur.execute("select publication_id from workbench.publication_heads where trade_date=%s", (trade_date,))
            if cur.fetchone() != (publication_id,):
                raise RuntimeError("PG publication head does not point to latest publication")
            cur.execute("select snapshot_id from workbench.publication_analysis_snapshots where publication_id=%s and domain='LOCAL_RECONSTRUCTED'", (publication_id,))
            if cur.fetchone() != (snapshot_id,):
                raise RuntimeError("PG publication analysis binding missing")
            cur.execute("select count(*) from workbench.analysis_snapshot_entries where snapshot_id=%s", (snapshot_id,))
            if int(cur.fetchone()[0]) != int(duck.execute("select count(*) from analysis_snapshot_entries where snapshot_id=?", [snapshot_id]).fetchone()[0]):
                raise RuntimeError("analysis snapshot entry count mismatch")
        pg.commit()
        report["status"] = "FULL_PASS"
        report["committed_at"] = datetime.now(timezone.utc).isoformat()
        return 0
    except Exception as exc:
        report["error"] = f"{type(exc).__name__}: {exc}"
        if pg is not None:
            pg.rollback()
        return 1
    finally:
        report["finished_at"] = datetime.now(timezone.utc).isoformat()
        args.report.parent.mkdir(parents=True, exist_ok=True)
        temp = args.report.with_suffix(args.report.suffix + ".tmp")
        temp.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        temp.replace(args.report)
        if pg is not None:
            pg.close()
        duck.close()
        print(json.dumps(report, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    raise SystemExit(main())
